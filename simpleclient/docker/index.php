<?php
if(!isset($_SESSION))
    session_start();
set_time_limit(0);
?>

<!doctype html>
<html lang="en">
<head>
    <!-- Required meta tags -->
    <meta charset="utf-8">
    <meta name="keywords" content="FAIR principles, assessment, evaluation, FAIR, research data, quality control, data maturity, metrics, digital objects">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.1/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-F3w7mX95PdgyTmZZMECAngseQB83DfGTowi0iMjiWaeVhAn4FJkqJByhZMI3AhiU" crossorigin="anonymous">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.5.0/font/bootstrap-icons.css">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.1/dist/js/bootstrap.bundle.min.js" integrity="sha384-/bQdsTh/da6pkI1MST/rWKFNjaCP5gBSY4sEBT38Q/9RBh9AH40zEOg7Hlq2THRZ" crossorigin="anonymous"></script>
    <style>
        .loader {
            border: 16px solid #f3f3f3; /* Light grey */
            border-top: 16px solid #3498db; /* Blue */
            border-radius: 50%;
            width: 80px;
            height: 80px;
            animation: spin 2s linear infinite;
            display: none;
            margin:auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    <link rel="icon" type="image/png" href="/icon/fuji_logo_square.png">
    <title>F-UJI simple client</title>
</head>
<body style="padding-bottom: 70px;">
    <nav class="navbar navbar-expand-lg navbar-light bg-light lead mb-4">
        <div class="container-fluid">
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarfuji" aria-controls="navbarfuji" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <a class="navbar-brand" href="#">
                <img src="/icon/fuji_logo_square.png" alt="" width="30" height="30" class="d-inline-block align-text-top"> <b>F-UJI simple client</b>
            </a>
        </div>
    </nav>
<?php
######################## local config ##########################
$fuji_server = 'http://fuji:1071/fuji/api/v1/evaluate';
$fuji_username = 'yourusername';
$fuji_password = 'yourpassword';
$usegithub = true;
################################################################

$fair_basic_terms=['F'=>'Findable','A'=>'Accessible','I'=>'Interoperable','R'=>'Reusable'];
$fair_index=['F'=>0,'A'=>1,'I'=>2,'R'=>3];
$maturity_scale = [0=>'incomplete',1=>'initial',2=>'moderate', 3=>'advanced'];
$status_scale = ['pass'=>'passed', 'fail'=>'not detected'];
$maturity_palette = array(0=>'#fe7d37',1=>'#dfb317',2=>'#97ca00',3=>'#4c1');
$maturity_level_text_array = array(0=>'incomplete',1=>'initial',2=>'managed',3=>'defined');

$input_service_type = 'oai_pmh';
$input_service_url ='';
if (isset($_POST['service_url'])){
    $input_service_url = $_POST['service_url'];
    if (isset($_POST['service_type'])){
        $input_service_type = $_POST['service_type'];
    }
}

if(!isset($_POST['use_datacite'])){
    $usedatacite=false;
}else{
    $usedatacite=true;
}
if (isset($_REQUEST['pid'])){
    $input_pid = $_REQUEST['pid'];
}else {
    $input_pid =Null;
}
if (isset($_POST['service_url'])){
    $input_service_url = $_POST['service_url'];
    if (isset($_POST['service_type'])){
        $input_service_type = $_POST['service_type'];
    }
}
if(isset($_POST['metric_version'])){
    $input_metric_version=$_POST['metric_version'];
}else{
    $input_metric_version="metrics_v0.7_software";
}

$allowed_service_types = array('oai_pmh'=>'OAI-PMH','ogc_csw'=>'OGC CSW', 'sparql'=>'SPARQL');
$allowed_metric_versions = array('metrics_v0.7_software'=>'software-agnostic', 'metrics_v0.7_software_cessda'=>'software-CESSDA')

?>
    <div class="container">
        <h1 class="my-4 display-4 pl-2">FAIR assessment</h1>
        <div class="row my-auto">
            <div class="col">
                <?php
                if(!isset($input_pid)){
                    echo('<div class="lead">
                        <p>F-UJI is a web service to programatically assess FAIRness of research data objects (aka data sets) based on metrics developed by the <a href="https://www.fairsfair.eu">FAIRsFAIR</a> project.</p>
                        <p class=" d-none d-lg-block">Please use the form below to enter an identifier (e.g. DOI, URL) of the data set you wish to assess. Optionally you also can enter a metadata service (OAI-PMH, SPARQL, CSW) endpoint URI which F-UJI can use to identify additional information.</p>
                        </div>');
                }
                ?>
                <div class="card bg-light mx-auto" id="assessment_form">
                    <div class="card-body">
                        <form class="form mb-3" action="index.php" method="POST">
                            <div class="row align-items-end">
                                <div class="col">
                                    <label for="pid" class="col-form-label-sm">Research Data Object (URL/PID):<sup style="color:red">*</sup></label>
                                    <input  class="form-control form-control-sm" type="text" value="<?php echo(htmlentities($input_pid ?? ''));?>" name="pid" id="pid" placeholder="Enter a valid PID or URL of the dataset's landing page (e.g. a DOI)">
                                </div>

                            </div>
                            <div class="row">
                                <div class="col ms-auto text-end">
                                    <a class="text-decoration-none" data-bs-toggle="collapse" href="#assessment_settings" role="button" aria-expanded="false" aria-controls="collapseExample">
                                        <i class="bi-gear-fill"></i> Settings
                                    </a>
                                </div>
                            </div>
                            <div class="collapse" id="assessment_settings">

                                <div class="row align-items-end">
                                    <div class="col-8">
                                        <label for="service_url" class="col-form-label-sm">(Optional) Metadata service endpoint:</label>
                                        <input  class="form-control form-control-sm" type="text" value="<?php echo(htmlentities($input_service_url ?? ''));?>" name="service_url" id="service_url" placeholder="(Optional) endpoint serving your metadata in different formats">
                                    </div>
                                    <div class="col-4">
                                        <label for="service_type" class="col-form-label-sm">Metadata service type:</label>
                                        <select class="form-select form-select-sm" name="service_type" id="service_type">
                                            <?php
                                            foreach($allowed_service_types as $sk=> $sv){
                                                if ($sk == $input_service_type)
                                                    echo '<option value ="'.$sk.'" selected>'.$sv.'</option>';
                                                else
                                                    echo '<option value ="'.$sk.'">'.$sv.'</option>';
                                            }
                                            ?>
                                        </select>
                                    </div>
                                    <div class="row align-items-end">
                                        <div class="col-8">
                                        <label for="metric_version" class="col-form-label-sm">Metric version:</label>
                                        <select class="form-select form-select-sm" name="metric_version" id="metric_version">
                                            <?php
                                            foreach($allowed_metric_versions as $mk=> $mv){
                                                if ($mk == $input_metric_version)
                                                    echo '<option value ="'.$mk.'" selected>'.$mv.'</option>';
                                                else
                                                    echo '<option value ="'.$mk.'">'.$mv.'</option>';
                                            }
                                            ?>
                                        </select>
                                        </div>
                                        <div class="col-4">
                                            <?php
                                            $usedatacite_checked = ' checked';
                                            if ($usedatacite == false)
                                                $usedatacite_checked = '';
                                            ?>
                                            <input type="checkbox" class="form-check-input" id="use_datacite" name="use_datacite" <?php echo($usedatacite_checked);?>>
                                            <label for="use_datacite" class="form-check-label ">
                                                <small>Use DataCite?</small>
                                            </label>
                                            &nbsp;<img src="../icon/bootstrap/question-circle.svg" alt="help" width="15" height="15" data-toggle="tooltip" title="By default, F-UJI uses content negotiation based on the DOI URL to retrieve DataCite JSON metadata. If you uncheck this option, F-UJI wil try to use the landing page URL instead.">

                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="d-flex justify-content-center">
                                <button type="input" class="btn btn-primary" name="runtest"><i class="bi-caret-right-fill"></i> Start FAIR Assessment</button>
                            </div>
                            <input type="hidden" name="action" value="test">
                        </form>
                    </div>
                </div>
                    <div class="alert d-none mt-1" role ="alert" id="test_message"></div>

            </div>
        </div>
<?php

if (isset($input_pid)) {
    $ch = curl_init();
    $message = new stdClass();
    $message->object_identifier = $input_pid;
    $message->metadata_service_endpoint = $input_service_url;
    $message->metadata_service_type = $input_service_type;
    $message->test_debug = true;
    $message->use_datacite = $usedatacite;
    $message->use_github = $usegithub;
    $message->metric_version = $input_metric_version;
    $post = json_encode($message);

    $username = $fuji_username;
    $password = $fuji_password;
    curl_setopt($ch, CURLOPT_URL, $fuji_server);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type:application/json', 'Allow-Remote-Logging:True'));
    curl_setopt($ch, CURLOPT_USERPWD, $username . ":" . $password);
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $post);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $server_output = curl_exec($ch);
    $response = json_decode($server_output, true);
    curl_close($ch);
    if(!isset($response)){
        print('<div class="alert alert-danger" role="alert">Server not responding </div>');
    }
}

    $debug_class_list=array('SUCCESS'=>'table-success','WARNING'=>'table-warning','ERROR'=>'table-danger');
    $fuji_percent_scores=array(0=>0,1=>0,2=>0,3=>0);
    $sections=array();

    if(isset($response['results'])){
        $metric_version = str_replace('.yaml','',$response['metric_version']);
        $software_version = $response['software_version'];
        $metric_doi = $response['metric_specification'];
        if(is_array($response['results'])){
            $total_score = 0;
            $earned_score =0;
            $percent_score =0;
            $pid_url = Null;
            $summary = $response['summary'];

            foreach ($response['results'] as $result) {
                $fair_letter=$result['metric_identifier'][4];
                if($result['metric_identifier']=='FsF-F2-01M'){
                    $metadata= $result['output']['core_metadata_found'];
                }
                if($result['metric_identifier']=='FsF-F1-02D'){
                    $pid_url= $result['output']['pid'];
                }
                $fair_section_regex = '/\-([FAIR][0-9](\.[0-9])?)\-/m';
                $fair_section='';
                if(preg_match($fair_section_regex,$result['metric_identifier'],$fair_section_match))
                    $fair_section =$fair_section_match[1];
                $fuji_results[$fair_letter][$result['metric_identifier']] = $result;
            }
            ?>
            <h2 class="h2 mt-4 mb-3">Assessment Results:</h2>
            <h3 class="h3 mb-3">Evaluated Resource:</h3>
            <div class="card mb-3">
                <h5 class="card-header"><?php
                    if(isset($metadata['title'])){
                        if(is_array($metadata['title']))
                            echo $metadata['title'][0];
                        else
                            echo(htmlentities($metadata['title']));
                    } else {
                        echo('&nbsp;');}?></h5>
                <div class="card-body p-2">

                    <table class="table mt-3 mb-3">
                        <tr>
                            <th>FAIR level:
                                &nbsp;<img src="../icon/bootstrap/question-circle.svg" alt="help" width="15" height="15" data-toggle="tooltip" title="0:incomplete, 1:initial , 2:moderate, 3:advanced">
                            </th>
                            <?php
                            $fair_maturity_color = $maturity_palette[round($summary['maturity']['FAIR'],0)];?>
                            <td><h4 class="h4 m-0"><span class="badge badge" style="color:white;background-color: <?php echo $fair_maturity_color;?>"><?php print($maturity_scale[round($summary['maturity']['FAIR'],0)]); ?></span></h4></td>
                        </tr>
                        <tr><th>Resource PID/URL:</th>
                        <?php
                            if(strpos($input_pid,'http') !==false){
                                ?>
                                <td class="text-break"><a <?php echo('href="'.$input_pid);?>"><?php echo(htmlentities($input_pid));?></a></td>
                                <?php
                            } else{
                            ?>
                                <td class="text-break"><?php echo(htmlentities($input_pid));?></td>
                                <?php }
                            ?>
                        </tr>
                        <tr><th>DataCite support:</th>
                            <td><?php print($usedatacite ? 'enabled' : 'disabled');?></td>
                        </tr>
                        <tr><th>GitHub support:</th>
                            <td><?php print($usegithub ? 'enabled' : 'disabled');?></td>
                        </tr>
                        <tr><th>Metric Version:</th>
                            <td><?php echo(htmlentities($metric_version));?></td>
                        </tr>
                        <tr><th>Metric Specification:</th>
                            <td><a href="<?php echo(htmlentities($metric_doi));?>"><?php echo(htmlentities($metric_doi));?></a></td>
                        </tr>
                        <tr><th>Software version:</th>
                            <td><?php echo(htmlentities($software_version));?></td>
                        </tr>
                    </table>
                </div>
            </div>
            <h3>Summary:</h3>
            <div class="card-group">
                <div class="card mb-3">
                    <div class="my-auto mx-auto p-3" style="max-width: 250px">
                        <span class="display-2 text-nowrap"><?php print($summary['score_percent']['FAIR']) ?>%</span>
                    </div>
                </div>
                <div class="card mb-3">
                    <table class="table table-bordered table-responsive">
                        <tr><th></th><th class="d-sm-none d-md-block">Score earned:</th><th>Fair level:</th></tr>
                    <?php
                    foreach(array('F','A','I','R') as $fairid){
                        ?>
                        <tr>
                            <th><?php echo($fair_basic_terms[$fairid].': ');?></th>
                            <td style="min-width: 110px"  class="d-sm-none d-md-block"><?php
                                    print($summary['score_earned'][$fairid]);
                                    print(' of ');
                                    print($summary['score_total'][$fairid]);
                                    ?>
                            </td>
                            <td>
                                <?php
                                if(isset($summary['maturity'])){
                                    $principle_maturity_color = $maturity_palette[$summary['maturity'][$fairid]];
                                ?>
                                <h4 class="h4 m-0"><span class="badge badge" style="color:white;background-color: <?php echo $principle_maturity_color;?>"><?php print($maturity_scale[$summary['maturity'][$fairid]]); ?></span></h4></td>

                                <?php
                                }
                                ?>
                            </td>
                        </tr>
                        <?php
                    }
                    ?>
                    </table>
                </div>
            </div>
            <?php
            print('<h3>Report:</h3>');
            foreach($fuji_results as $fair_index=>$fuji_fairsection){
                print('<h4 class="h-4 mb-3 mt-3 fst-italic">'.$fair_basic_terms[$fair_index].'</h4>');
                print('<div class="accordion" id="accordion_'.$fair_index.'">');
                $test_index=0;
                foreach($fuji_fairsection as $fuji_res){
                    $test_index++;
                    print('<div class="class="accordion-item mb-3">');
                    print('<h2 class="accordion-header lead border border-1 mt-1" id="head_'.$fuji_res['metric_identifier'].'">');
                    print('<button class="accordion-button collapsed" data-bs-toggle="collapse" 
                    data-bs-target="#body_'.$fair_index.'_'.$test_index.'" aria-expanded="false" 
                    aria-controls="body_'.$fair_index.'_'.$test_index.'">');
                    print('<h5 class="h-5  text-muted" style="width:90%">');
                    print($fuji_res['metric_identifier'].' - '.$fuji_res['metric_name']);
                    print('</h5>');

                    if($fuji_res['maturity'] >= 1)
                        print('<img style="margin-left:auto; width:30px; float:right" src="/icon/passed_'.$fuji_res['maturity'].'.png">');
                    elseif(!is_int($fuji_res['maturity'])){
                        if($fuji_res['test_status']=='pass')
                            print('<img style="margin-left:auto; width:30px; float:right" src="/icon/passed.png">');
                        else
                            print('<img style="margin-left:auto; width:30px; float:right" src="/icon/unknown.png">');
                    }
                    else
                        print('<img style="margin-left:auto; width:30px; float:right" src="/icon/unknown.png">');
                    print('</button></h2>');
                    print('<div class="accordion-collapse collapse" aria-labelledby="head_'.$fair_index.'_'.$test_index.'" id="body_'.$fair_index.'_'.$test_index.'" data-parent="#accordion_'.$fair_index.'">');
                    print('<div class="accordion-body border rounded-1 border-1">');

                    if (!is_int($fuji_res['maturity'])){
                        $maturity_key = array_search($fuji_res['maturity'],$maturity_scale_old);
                        if($maturity_key!==False) {
                            $fuji_res['maturity'] = $maturity_key;
                            $scaled_maturity = $maturity_scale[$maturity_key];
                            $maturity_color = $maturity_palette[$maturity_key];
                        }else {
                            $scaled_maturity = $fuji_res['maturity'];
                            $maturity_color = 'grey';
                        }
                    }else{
                        $scaled_maturity = $maturity_scale[$fuji_res['maturity']];
                        $maturity_color = $maturity_palette[$fuji_res['maturity']];
                    }
                    print('<div class="row mb-2">
                            <div class="col-md-2"><b>FAIR level:</b></div>
                            <div class="col-md-8">'.$fuji_res['maturity'].' of 3 </div>');
                    print('<div class ="col-md-2 text-right">
                            <span class="badge badge" style="color:white;background-color: '.$maturity_color.'">'.$scaled_maturity.'</span>
                            </div>');
                    print('</div>');
                    print('<div class="row mb-2"><div class="col-md-2"><b>Score:</b></div><div class="col-md-10">');
                    print($fuji_res['score']['earned'].' of '.$fuji_res['score']['total']);
                    print('</div></div>');
                    print('<div class="row mb-2"><div class="col-md-2"><b>Output:</b></div><div class="col-md-10">');
                    print('<pre><code>'.htmlspecialchars(json_encode($fuji_res['output'], JSON_PRETTY_PRINT)).'</code></pre>');
                    print('</div></div>');
                    print('<div class="row mb-3"><div class="col-md-2"><b>Metric tests:</b></div><div class="col-md-10">');
                    print('<table class="table w-100"><tr><th>Test:</th><th>Test name:</th><th>Score:</th><th>Maturity:</th></th><th>Result:</th></tr>');
                    foreach($fuji_res['metric_tests'] as $test_key=>$metric_test){
                        if(preg_match('/-[0-9]{1}([a-z]{1})$/',$test_key,$tm)){
                            $mstyle=' style="font-size:smaller"';
                            $test_key = '&nbsp;&nbsp;'.$tm[1];
                        }else{
                            $mstyle='';
                        }
                        print('<tr'.$mstyle.'><th scope="row">'.$test_key.'</th><td>'.$metric_test['metric_test_name'].'</td><td>');
                        if($metric_test['metric_test_score']['earned'] !=0){
                            print($metric_test['metric_test_score']['earned']);
                        }
                        print('</td><td>');
                        if($metric_test['metric_test_status']=='pass'){
                            print($metric_test['metric_test_maturity']);
                        }
                        print('</td><td>');
                        if($metric_test['metric_test_status']=='pass')
                            print('<img class="mx-auto d-block" style="width:30px;" src="/icon/passed.png">');
                        else
                            print('<img class="mx-auto d-block" style="width:30px;" src="/icon/unknown.png">');
                        print('</td></tr>');
                    }
                    print('</table>');
                    print('</div></div>');
                    print('<div class="row"><div class="col-md-2"><b>Debug messages:</b></div><div class="col-md-10">');
                    print('<table class="table table-sm w-100 table-striped table-bordered"><tr><th>Level:</th><th>Message:</th></tr>');
                    foreach($fuji_res['test_debug'] as $debug_message){
                        if(preg_match('/([A-Z]+):\s+(.*+)/',$debug_message,$debug_regex_result)) {
                            if(array_key_exists($debug_regex_result[1],$debug_class_list)){
                                $debug_class=' class="debug_'.$debug_regex_result[1].' '.$debug_class_list[$debug_regex_result[1]].'"';
                            }
                            else
                                $debug_class='';
                            print('<tr'.$debug_class.'><th scope="row">'.$debug_regex_result[1].'</th><td>'.$debug_regex_result[2].'</td></tr>');
                        }
                    }
                    print('</table>');
                    print('</div></div>');

                    print('</div></div>');
                    print('</div>');
                }
                print('</div>');
            }
        }
    }elseif(isset($response['status'])){
        if ($response['status']==401) {
            print('<div id="fuji_error" class="alert alert-danger">');
            print('<b>Authorisation failed</b>');
            print('</div>');
        }
        elseif ($response['status']==500) {
            print('<div id="fuji_error" class="alert alert-danger">');
            print('<b>'.$response['title'].'</b>');
            print('<br>');
            print($response['detail']);
            print('<br> If this error persists please report at: <a href="https://github.com/pangaea-data-publisher/fuji/issues">
            https://github.com/pangaea-data-publisher/fuji/issues</a>');
            print('</div>');
        }else{
            print('<div id="fuji_error" class="alert alert-danger">');
            print('<b>Response code: </b>'.$response['status']);
            print('</div>');
        }
    }
    ?>
<div class="navbar">
    <div class="container text-center justify-content-center">
        <div class="justify-content-center">
            F-UJI is a result of the <a href="https://www.fairsfair.eu">FAIRsFAIR</a> “Fostering FAIR Data Practices In Europe”
            project which received funding from the European Union’s Horizon 2020 project call H2020-INFRAEOSC-2018-2020 (grant agreement 831558).
        </div>
    </div>
</div>
</body>
</html>
