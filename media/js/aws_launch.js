var WARN_NODES = 100;

/**
 * Node counts
 */

function thorNodeCount() {
    return $('#id_thor_nodes').val() | 0;
}

function roxieNodeCount() {
    return $('#id_roxie_nodes').val() | 0;
}    

/**
 * Confirm the size of cluster to launch with the user
 */
function confirmLaunch(){
    //  Double check the form again, to prevent JS injection submit
    if (!$('#launch_form, #advanced_launch_form').valid()){
        return false;
    }
    //  Verify number of nodes
    if (thorNodeCount() + roxieNodeCount() > WARN_NODES){
        return confirm('Are you sure you want to launch cluster with over ' + WARN_NODES + ' nodes?');
    }
    //
    return true;
}

//
$(document).ready(function(){
    var MIN_NODES = 1;
    var MAX_NODES = parseInt($('#hdnMaxNodes').val());

    //  Launch Form
    if ($('#launch_form, #advanced_launch_form')) {

        //  Form Validation
        $('#launch_form, #advanced_launch_form').validate({
            errorLabelContainer: $('#error-box'),
            rules: {
                thor_nodes:{
                    required: true,
                    digits: true,
                    min: function() { return roxieNodeCount() > 0 ? 0 : MIN_NODES },
                    max: MAX_NODES
                },
                roxie_nodes:{
                    required: true,
                    digits: true,
                    min: function() { return thorNodeCount() > 0 ? 0 : MIN_NODES },
                    max: MAX_NODES
                }
            }
        });

        /**
         * Calculates number of noted to launch
         */
        function calculateNodes(roxieFirst) {
            var thorNodes = parseInt(thorNodeCount());
            var roxieNodes = parseInt(roxieNodeCount());            
            var mainNodes = thorNodes + roxieNodes;
            var supportNodes = 0;

            if (mainNodes > MAX_NODES){
                var excessNodes = mainNodes - MAX_NODES;
                if (roxieFirst) {
                    roxieNodes = roxieNodes <= excessNodes ? 0 : roxieNodes - excessNodes;
                    thorNodes = MAX_NODES - roxieNodes;                
                } else {
                    thorNodes = thorNodes <= excessNodes ? 0 : thorNodes - excessNodes;
                    roxieNodes = MAX_NODES - thorNodes;
                }
                mainNodes = thorNodes + roxieNodes;
                $('#id_thor_nodes').val(thorNodes);
                $('#id_roxie_nodes').val(roxieNodes);
                alert('Please contact us at info@hpccsystems.com for requests larger than ' + MAX_NODES + '.');
            }
            if (mainNodes <= 1){
                supportNodes = 0;
            }else if (mainNodes <= 10){
                supportNodes = 1;
            }else if (mainNodes <= 20){
                supportNodes = 2;
            }else if (mainNodes <= 50){
                supportNodes = 3;
            }else if (mainNodes <= 100){
                supportNodes = 4;
            }else if (mainNodes <= 500){
                supportNodes = 5;
            }else{
                supportNodes = 7;
            }

            $('#id_node_count').val(supportNodes + mainNodes);
            $('#id_support_nodes').val(supportNodes);
        }

        var position = {
            my: 'left center',
            at: 'right center'
        }

        $('#id_thor_nodes').qtip({
            content: 'Enter the number of Thor compute nodes you want to start (' + MIN_NODES + '-' + MAX_NODES + ').',
            position: position
        });

        $('#id_roxie_nodes').qtip({
            content: 'Enter the number of Roxie query nodes you want to start (' + MIN_NODES + '-' + MAX_NODES + ').',
            position: position
        });

        $('#id_node_count').qtip({
            content: 'This is the total number of nodes your cluster will have.',
            position: position
        });

        $('#id_support_nodes').qtip({
            content: 'This indicates the number of additional nodes needed for support functions, varies with the cluster size.',
            position: position
        });

        $('#id_region').qtip({
            content: 'The Oregon region is recommended due to the newer hardware, fewer system errors, and lower prices.',
            position: position
        });

        $('#id_ebs_storage_ids').qtip({
            content: 'Optionally enter snapshot IDs for data you would like attached to the cluster landing zone.  Multiple entries can be comma, space, or semicolon delimited.',
            position: position
        });

        //  Set Binding
        $('#id_thor_nodes').change(function() {
            calculateNodes(true);
        }).keyup(function() {
            calculateNodes(true);
        }).trigger('change');
        $('#id_roxie_nodes').change(function() {
            calculateNodes(false);
        }).keyup(function() {
            calculateNodes(false);
        }).trigger('change');
        $('#id_thor_nodes, #id_roxie_nodes').keydown(function(event) {
            // Allow: backspace, delete, tab and escape
            if ( event.keyCode == 46 || event.keyCode == 8 || event.keyCode == 9 || event.keyCode == 27 ||
                // Allow: Ctrl+A
                (event.keyCode == 65 && event.ctrlKey === true) ||
                // Allow: home, end, left, right
                (event.keyCode >= 35 && event.keyCode <= 39)) {
                // let it happen, don't do anything
                return;
            } else {
                // Ensure that it is a number and stop the keypress
                if ((event.keyCode < 48 || event.keyCode > 57) && (event.keyCode < 96 || event.keyCode > 105 )) {
                    event.preventDefault();
                }
            }
        });
    
        calculateNodes(true);
    }
});
