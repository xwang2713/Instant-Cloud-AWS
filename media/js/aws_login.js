$(document).ready(function() {
    //  Form Validation
    $("#login_form").validate({
        rules: {
            access_key_id:{
                required: true,
                minlength: 20,
                maxlength: 20
            },
            secret_access_key:{
                required: true
            },
            terms_of_use:{
                required: true
            }            
        }
    });
        
    $('#termsOfUse').change(function(){
        var isAccepted = ($('#termsOfUse').is(':checked')) ? 'True' : 'False';
        $('#id_terms_of_use').val(isAccepted);
    });

    $('#id_access_key_id').qtip({
        content: 'Enter your Access Key ID, a 20 character string, NOT your Amazon Login ID.<br /><br />See the "AWS Access Keys" link below.',
        position: {
            my: 'top center',
            at: 'bottom center',
            target: $('#id_access_key_id')
        }
    });

    $('#id_secret_access_key').qtip({
        content: 'Enter your Secret Access Key, a very long character string, NOT your Amazon password.<br /><br />See the "AWS Access Keys" link below.',
        position: {
            my: 'top center',
            at: 'bottom center',
            target: $('#id_secret_access_key')
        }
    });
    
});