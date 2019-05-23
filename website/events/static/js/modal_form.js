function open_modal(url)
{
        $('#popup').load(url, function()
        {
                $(this).modal('show');
        });
        return false;
}

function close_modal()
{
        $('#popup').modal('hide');
        return false;
}

$(document).ready(function()
{
    
});