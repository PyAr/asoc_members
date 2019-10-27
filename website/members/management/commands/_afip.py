import os
from decimal import Decimal

from pyafipws.wsaa import WSAA
from pyafipws.wsfev1 import WSFEv1
from pyafipws.pyfepdf import FEPDF

from django.conf import settings

CACHE = "/tmp/pyafip-cache-real"
CONFIG_PDF = {
    'LOGO': "static/images/acpyar.png",
    'EMPRESA': "Asociación Civil Python Argentina",
    'MEMBRETE1': "Chile 1155 piso 1 - CABA",
    'CUIT': "CUIT 30-71563912-9",
    'IIBB': "Exento",
    'IVA': "IVA Responsable Inscripto",
    'INICIO': "Inicio de Actividad: 19/02/2016",
}

PDF_PATH = "/tmp"

INVOICE_TYPE = 6


def generate_invoices(records):
    """Generate the invoices in PDF using AFIP API resources."""
    # AFIP init
    wsaa = WSAA()
    wsfev1 = WSFEv1()

    # get access ticket (token y sign)
    certificate = settings.AFIP['auth_cert_path']
    private_key = settings.AFIP['auth_key_path']
    if not os.path.exists(certificate):
        raise ValueError("Auth certificate can not be found (got {!r})".format(certificate))
    if not os.path.exists(private_key):
        raise ValueError("Auth key can not be found (got {!r})".format(private_key))
    ta = wsaa.Autenticar(
        "wsfe", certificate, private_key, wsdl=settings.AFIP['url_wsaa'], cache=CACHE, debug=True)
    wsfev1.Cuit = settings.AFIP['cuit']
    wsfev1.SetTicketAcceso(ta)
    wsfev1.Conectar(CACHE, settings.AFIP['url_wsfev1'])

    # basic initial check
    last_auth_invoice = wsfev1.CompUltimoAutorizado(INVOICE_TYPE, settings.AFIP['selling_point'])
    print("Last authorized invoice", last_auth_invoice)
    # res = wsfev1.CompConsultar(INVOICE_TYPE, last_auth_invoice, settings.AFIP['selling_point'])
    # print("======== AFIP current status", res)

    # init PDF builder
    fepdf = FEPDF()
    fepdf.CargarFormato("factura.csv")
    fepdf.FmtCantidad = "0.2"
    fepdf.FmtPrecio = "0.2"
    fepdf.CUIT = settings.AFIP['cuit']
    for k, v in CONFIG_PDF.items():
        fepdf.AgregarDato(k, v)

    # safeguard when using test webservice endpoints
    if "homo" in settings.AFIP['url_wsaa']:
        fepdf.AgregarCampo(
            "DEMO", 'T', 120, 260, 0, 0, text="DEMOSTRACION",
            size=70, rotate=45, foreground=0x808080, priority=-1)
        fepdf.AgregarDato("motivos_obs", "Ejemplo Sin Validez Fiscal")

    # get CAE for each record and generate corresponding PDF
    results = {}
    for record in records:
        invoice = MemberInvoice(
            document_number=record['dni'], fullname=record['fullname'],
            address=record['address'], city=record['city'], zip_code=record['zip_code'],
            province=record['province'], invoice_date=record['invoice_date'],
            invoice_number=record['invoice'],
            service_date_from=record['service_date_from'],
            service_date_to=record['service_date_to'])
        invoice.add_item(
            description=record['description'], quantity=record['quantity'],
            amount=record['amount'], comment=record['payment_comment'])

        authorized_ok = invoice.autorizar(wsfev1)
        invoice_number = invoice.header["cbte_nro"]
        print("    invoice generated: number={} CAE={} authorized={}".format(
            invoice_number, invoice.header["cae"], authorized_ok))
        results[invoice_number] = {'invoice_ok': authorized_ok}
        if not authorized_ok:
            print("WARNING not auth")
            return

        # another safeguard
        if "homo" in settings.AFIP['url_wsfev1']:
            invoice.header["motivos_obs"] = "Ejemplo Sin validez fiscal"

        # generate the PDF
        pdf_name = "FacturaPyArAC-{:04d}-{:08d}.pdf".format(
            settings.AFIP['selling_point'], invoice_number)
        pdf_path = os.path.join(PDF_PATH, pdf_name)
        invoice.generate_pdf(fepdf, pdf_path)
        print("    PDF generated {!r}".format(pdf_path))
        results[invoice_number]['pdf_path'] = pdf_path

    return results


class MemberInvoice:
    """Specific invoice with hardcoded values for members."""

    def __init__(
            self, document_number, fullname, address, city, zip_code, province,
            invoice_number, invoice_date, service_date_from, service_date_to):

        self.header = dict(
            # defaults for this invoice type
            tipo_cbte=INVOICE_TYPE,
            tipo_doc=96,
            punto_vta=settings.AFIP['selling_point'],
            concepto=3,  # servicios

            # for this invoice in particular
            nro_doc=document_number,
            nombre_cliente=fullname,
            domicilio_cliente=address,
            localidad="{} ({})".format(city, zip_code),
            provincia=province,
            cbte_nro=invoice_number,
            fecha_cbte=invoice_date.strftime("%Y%m%d"),
            fecha_serv_desde=service_date_from,
            fecha_serv_hasta=service_date_to,
            fecha_venc_pago=invoice_date.strftime("%Y%m%d"),

            # lot of defaults
            imp_total=Decimal(0), imp_tot_conc=Decimal(0), imp_neto=Decimal(0),
            imp_trib=Decimal(0), imp_op_ex=Decimal(0), imp_iva=Decimal(0),
            moneda_id='PES', moneda_ctz=1.000,
            pais_dst_cmp=200, id_impositivo='Consumidor Final',
            motivo_obs="", cae="", resultado='', fch_venc_cae=""
        )
        self.cmp_asocs = []
        self.items = []
        self.ivas = {}

    def add_item(self, description, quantity, amount, comment):
        """Add the billed service."""
        item = dict(
            u_mtx=123456,
            cod_mtx=1234567890123,
            codigo="",
            ds=description + "\n" + comment,
            qty=quantity,
            umed=7,
            bonif=0.00,
            despacho=u'Nº 123456',
        )
        subtotal = amount * quantity
        self.header["imp_total"] += subtotal
        self.header["imp_op_ex"] += subtotal
        item["iva_id"] = 3  # 0%
        item["precio"] = amount
        item["imp_iva"] = None
        item["importe"] = subtotal
        self.items.append(item)

    def autorizar(self, wsfev1):
        "Prueba de autorización de un comprobante (obtención de CAE)"
        self.header["cbt_desde"] = self.header["cbte_nro"]
        self.header["cbt_hasta"] = self.header["cbte_nro"]
        wsfev1.CrearFactura(**self.header)

        # agrego un comprobante asociado (solo notas de crédito / débito)
        for cmp_asoc in self.cmp_asocs:
            wsfev1.AgregarCmpAsoc(**cmp_asoc)

        # agrego el subtotal por tasa de IVA (iva_id 5: 21%):
        for iva in self.ivas.values():
            wsfev1.AgregarIva(**iva)

        # llamo al websevice para obtener el CAE:
        wsfev1.CAESolicitar()

        if wsfev1.ErrMsg:
            raise RuntimeError(wsfev1.ErrMsg)

        for obs in wsfev1.Observaciones:
            print("WARNING", obs)

        authorized_ok = wsfev1.Resultado == "A" and bool(wsfev1.CAE) and bool(wsfev1.Vencimiento)

        self.header["resultado"] = wsfev1.Resultado
        self.header["cae"] = wsfev1.CAE
        self.header["fch_venc_cae"] = wsfev1.Vencimiento
        return authorized_ok

    def generate_pdf(self, fepdf, filepath):
        """Generate the invoice image."""
        fepdf.CrearFactura(**self.header)

        # completo campos extra del header:
        fepdf.EstablecerParametro("localidad_cliente", self.header["localidad"])
        fepdf.EstablecerParametro("provincia_cliente", self.header["provincia"])

        # imprimir leyenda "Comprobante Autorizado" (constatar con WSCDC!)
        fepdf.EstablecerParametro("resultado", self.header["resultado"])

        # detalle de artículos:
        for item in self.items:
            fepdf.AgregarDetalleItem(**item)

        # agrego remitos y otros comprobantes asociados:
        for cmp_asoc in self.cmp_asocs:
            fepdf.AgregarCmpAsoc(**cmp_asoc)

        # agrego el subtotal por tasa de IVA (iva_id 5: 21%):
        for iva in self.ivas.values():
            fepdf.AgregarIva(**iva)

        # armar el PDF:
        fepdf.CrearPlantilla(papel="A4", orientacion="portrait")
        fepdf.ProcesarPlantilla(num_copias=1, lineas_max=24, qty_pos='izq')
        fepdf.GenerarPDF(archivo=filepath)
