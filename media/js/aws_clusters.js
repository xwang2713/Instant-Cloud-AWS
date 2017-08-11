$(document).ready(function() {
    var defaultPos = {
        my: 'bottom center', 
        at: 'top center'
    } 
    
    $('#colLaunchDate').qtip({
        content: 'Date the cluster was launched.',
        position: defaultPos
    });
    $('#colCluster').qtip({
        content: 'Name of the cluster',
        position: defaultPos
    });
    $('#colNodes').qtip({
        content: 'Total number of nodes in the cluster',
        position: defaultPos
    });
    $('#colAvailability').qtip({
        content: 'Distinct location where cluster is placed',
        position: defaultPos
    });
    $('#colEspPage').qtip({
        content: 'ESP IP address and link to ESP Page.<br/>This IP is also used by the ECL IDE.',
        position: defaultPos
    });
    $('#colStatus').qtip({
        content: 'Current status of the cluster',
        position: defaultPos
    });
    $('#colLaunchLog').qtip({
        content: 'Link to the Thor Cluster&trade; log',
        position: defaultPos
    });
    $('#colConfig').qtip({
        content: 'Link to the cluster configuration file',
        position: defaultPos
    });
    $('#colIpAddresses').qtip({
        content: 'Link to the page with all IPs for the cluster',
        position: defaultPos
    });
    $('#colSshKey').qtip({
        content: 'Link to download/delete PEM SSH Key for the Thor&trade; Cluster',
        position: defaultPos
    });
    $('#colTerminates').qtip({
        content: 'Link to terminate running cluster',
        position: defaultPos
    });
    
    // add tips to all esp-links
    $('a.esp-link').qtip({
        content: 'ESP IP address, also used by the ECL IDE',
        position: {
            my: 'left center', 
            at: 'right center'
        } 
    });
});