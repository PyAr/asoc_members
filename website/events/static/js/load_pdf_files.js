$(document).ready(function()
{   
    if($('#invoice-pdf-div').length){
		url = $('#invoice-pdf-div').attr('invoice-url');
		var pdfjsLib = window['pdfjs-dist/build/pdf'];
		//pdfjsLib.GlobalWorkerOptions.workerSrc = $('#invoice-pdf-div').attr('worker-url');
		pdfjsLib.GlobalWorkerOptions.workerSrc = '//mozilla.github.io/pdf.js/build/pdf.worker.js';
		var loadingTask = pdfjsLib.getDocument(url);
		loadingTask.promise.then(function(pdf) {
		console.log('PDF loaded');
		
		// Fetch the first page
		var pageNumber = 1;
		pdf.getPage(pageNumber).then(function(page) {
			console.log('Page loaded');
			
			var scale = 1.5;
			var viewport = page.getViewport({scale: scale});

			// Prepare canvas using PDF page dimensions
			var canvas = document.getElementById('pdf-canvas');
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
        //renderPDF(url, $('#invoice-pdf-div'));
    }

});