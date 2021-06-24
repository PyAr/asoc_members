var pdfjsLib = window['pdfjs-dist/build/pdf'];
pdfjsLib.GlobalWorkerOptions.workerSrc = '//mozilla.github.io/pdf.js/build/pdf.worker.js';

$(document).ready(function()
{   
	function renderPDF(url, canvas, width){
		var loadingTask = pdfjsLib.getDocument(url);
		loadingTask.promise.then(function(pdf) {
			console.log('PDF loaded');
			
			// Fetch the first page
			var pageNumber = 1;
			pdf.getPage(pageNumber).then(function(page) {
				console.log('Page loaded');
				pageWidth = page.getViewport({scale: 1}).width;
				var scale = 1;
				if (pageWidth > width)
				{
					scale = width/page.getViewport({scale: 1}).width;
				}
				var viewport = page.getViewport({scale: scale});
	
				// Prepare canvas using PDF page dimensions
				var context = canvas.getContext('2d');
				canvas.height = viewport.height;
				canvas.width = viewport.width;
	
				// Render PDF page into canvas context
				var renderContext = {
					canvasContext: context,
					viewport: viewport
				};
				var renderTask = page.render(renderContext);
				renderTask.promise.then(function () {
					console.log('Page rendered');
				});
			});
			}, function (reason) {
				// PDF loading error
				console.error(reason);
			});
	}

  if($('#invoice-pdf-div').length){
		url = $('#invoice-pdf-div').attr('invoice-url');
		canvas = document.getElementById('pdf-canvas');
		renderPDF(url, canvas, 450);
	}

	// if there are invoice affects read all pdf's 
	if($('.pdf-affect').length){
		$('.pdf-affect').each(function(index){
			//TODO
			url = $(this).attr('affect-url');
			canvas = $(this).children('canvas')[0];
			renderPDF(url, canvas, 200);
		});
	}
	// if there are payment read all pdf's 
	if($('#pdf-payment').length){
		//TODO
		url = $('#pdf-payment').attr('payment-url');
		canvas = $('#pdf-payment').children('a').children('canvas')[0];
		renderPDF(url, canvas, 350);
		
	}


	

});