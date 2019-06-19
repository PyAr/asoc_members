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


function open_confirm_dialog()
{
        $('#confirm-dialog').modal('show');
        return false;
}

function close_confirm_dialog()
{
        $('#confirm-dialog').modal('hide');
        return false;
}

$(document).ready(function()
{
    
});