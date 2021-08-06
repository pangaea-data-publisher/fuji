#!/usr/bin/env python3

import configparser as ConfigParser
import io
import json
import logging
import os
from pathlib import Path
from fuji_server.controllers.fair_check import FAIRCheck
from fuji_server.helper.preprocessor import Preprocessor
import gc
import tracemalloc
# os
#os.environ['TIKA_SERVER_JAR'] = 'file://Program Files\tika\tika-server-1.24.1.jar'

identifier = 'https://doi.org/10.1594/PANGAEA.902845'
#identifier='https://doi.org/10.26050/WDCC/MOMERGOMBSCMAQ'
#oai_pmh = 'http://ws.pangaea.de/oai/'
debug = True

muchotestpids=[
    '10.15493/DEFF.10000003','https://phaidra.cab.unipd.it/view/o:267291','https://jyx.jyu.fi/handle/123456789/39205',
    'doi:10.1038/nphys1170','doi:10.17882/42182','https://deims.org/sites/default/files/data/elter_va_fruska_gora_temperature_0.xls',
    '10.25504/FAIRsharing.2bdvmk','http://bio2rdf.org/affymetrix:1415765_at','doi:10.18129/B9.bioc.BiocGenerics',
    'https://data.noaa.gov/dataset/dataset/w00411-nos-hydrographic-survey-2015-08-15','10.6075/J0513WJD','10.7280/D1P075',
    '10.1007/s10531-013-0468-6','https://neurovault.org/images/13953/','10.17605/OSF.IO/XFWS6','https://hdl.handle.net/10411/G8MPEI',
    '10.17870/bathspa.7926890.v1','http://thredds.met.no/thredds/catalog/met.no/observations/stations/catalog.html?dataset=met.no/observations/stations/SN999',
    'https://hdl.handle.net/11676/Hz8P-d-sstjMXCmWGTY67a2O','10.24435/materialscloud:2019.0013/v2','https://www.gbif.org/dataset/4a65dba1-ff0d-4e72-aa3c-e76e48856930',
    'hdl:10037.1/10152','https://repo.clarino.uib.no/xmlui/handle/11509/95','https://hunt-db.medisin.ntnu.no/hunt-db/#/studypart/432',
    'https://www.proteinatlas.org/ENSG000002695','http://gis.ices.dk/geonetwork/srv/eng/catalog.search#/metadata/33fa648d-c4d6-4449-ac3c-dbec0f204e1d',
    'https://data.geus.dk/JupiterWWW/anlaeg.jsp?anlaegid=97389','http://tun.fi/JX.1058739','10.15468/0fxsox',
    'https://doi.pangaea.de/10.1594/PANGAEA.866933','10.17026/dans-z56-fz75','http://data.europa.eu/89h/jrc-eplca-898618b5-3306-11dd-bd11-0800200c9a66',
    'https://www.govdata.de/web/guest/suchen/-/details/temperatur-des-meerwassers-20172b0eb','doi:10.26050/WDCC/MOMERGOMBSCMAQ',
    'https://lithologs.net/?action=view&oid=470','http://bio2rdf.org/affymetrix:1415765_at','https://www.data.gv.at/katalog/dataset/b8dac7af-5c8a-4936-9abe-e1dbbdd8dd4f',
    'https://identifiers.org/ena.embl:BN000065','https://www.ebi.ac.uk/biosamples/samples/SAMN14168013','https://data.gov.lv/dati/lv/dataset/covid-19',
    'https://www.data.gouv.fr/datasets/5e7e104ace2080d9162b61d8','https://www.data.gv.at/katalog/dataset/b8dac7af-5c8a-4936-9abe-e1dbbdd8dd4f',
    'https://datos.gob.es/es/catalogo/e05070101-evolucion-de-enfermedad-por-el-coronavirus-covid-19','https://doi.org/10.26050/WDCC/MOMERGOMBSCMAQ',
    'https://data.gov.lv/dati/lv/dataset/covid-19','https://raw.githubusercontent.com/obi-ontology/obi/v2020-04-23/obi.owl','http://vocab.nerc.ac.uk/collection/L22/current/',
    'http://purl.org/vocommons/voaf','http://purl.obolibrary.org/obo/bfo.owl','http://purl.obolibrary.org/obo/bfo.owl',
    'https://raw.githubusercontent.com/BFO-ontology/BFO/v2019-08-26/bfo_classes_only.owl','http://vocab.nerc.ac.uk/collection/L05/current/',
    'https://doi.org/10.4232/1.13491','http://dx.doi.org/10.18712/NSD-NSD2202-2-v1','http://doi.org/10.5255/UKDA-SN-854270', 'https://doi.org/10.1594/PANGAEA.896660',
    'http://sweetontology.net/matrRockIgneous','http://hdl.handle.net/20.500.12124/7','http://hdl.handle.net/11495/DAB8-B44B-E8C8-2','https://doi.pangaea.de/10.1594/PANGAEA.919306',
    'https://doi.org/10.7302/Z24Q7S64','10.5676/DWD_GPCC/MP_M_V6_100','10.6092/84cb588d-97e5-4c64-91bb-ba6109dfa530',
    'https://doi.org/10.17863/CAM.14473','doi:10.5441/001/1.44cb3946','https://doi.org/10.25704/Z5Y2-QPYE','https://cera-www.dkrz.de/WDCC/ui/cerasearch/entry?acronym=CMAQ_t_det_w_atmos_tot_N_17',
    'http://doi.org/10.25914/5eaa30de53244','http://dx.doi.org/10.4227/05/5344F1159A1A9','https://deims.org/dataset/75a7f938-7c77-11e3-8832-005056ab003f',
    'https://hdl.handle.net/11676/Ok72Hfm8xlJkhg-9lOQpsZGr','https://data.neonscience.org/data-products/DP1.20066.001','https://doi.pangaea.de/10.1594/PANGAEA.920063',
    'https://doi.pangaea.de/10.1594/PANGAEA.896543','https://dx.doi.org/10.4227/05/5344F1159A1A9','https://doi.org/10.4225/08/563869A931CFE',
    'https://data.neonscience.org/data-products/DP1.00001.001','https://dx.doi.org/10.11922/sciencedb.293','https://deims.org/dataset/75a7f938-7c77-11e3-8832-005056ab003f',
    'https://meta.icos-cp.eu/objects/8YwZj8CQEj87IuI9P6QkZiKX','http://doi.org/10.22033/ESGF/CMIP6.4397','http://doi.org/10.25914/5eaa30de53244',
    'http://dda.dk/catalogue/150','https://doi.org/10.1594/PANGAEA.902845','https://doi.org/10.1594/PANGAEA.745671','http://dda.dk/catalogue/150','https://ckan.govdata.de/ja/dataset/bebauungsplan-rahlstedt-131-hamburgb809f',
    'https://deims.org/dataset/75a7f938-7c77-11e3-8832-005056ab003f','https://hdl.handle.net/11168/11.429265',
    'https://metadata.bgs.ac.uk/geonetwork/srv/api/records/6abc401d-250a-5469-e054-002128a47908','https://data.dtu.dk/articles/Data_for_the_paper_A_dual_reporter_system_for_investigating_and_optimizing_translation_and_folding_in_E_coli_/10265420',
    'https://www.proteinatlas.org/ENSG00000110651-CD81/cell','http://dda.dk/catalogue/868','https://ckan.govdata.de/ja/dataset/bebauungsplan-rahlstedt-65-hamburg', 'https://ortus.rtu.lv/science/en/datamodule/294',
    'https://doi.org/10.15482/USDA.ADC/1324677','https://www.proteinatlas.org/ENSG00000110651-CD81/cell','http://doi.org/10.5255/UKDA-SN-1329-1',
    'http://purl.org/vocommons/voaf','https://meta.icos-cp.eu/objects/9ri1elaogsTv9LQFLNTfDNXm','http://doi.org/10.22033/ESGF/CMIP6.4397',
    'https://su.figshare.com/articles/Data_for_Does_historical_land_use_affect_the_regional_distribution_of_fleshy-fruited_woody_plants_Arnell_et_al_2019_/10318046','http://doi.org/10.1007/s10531-013-0468-6',
    'https://data.gov.lv/dati/lv/dataset/maksatnespejas-procesi','https://databank.ora.ox.ac.uk/UniversityCollege/datasets/04156fde-dabb-48fd-baf6-533182f74b5b',
    'https://repo.clarino.uib.no/xmlui/handle/11509/103','https://data.aussda.at/dataset.xhtml?persistentId=doi:10.11587/QQ7HTL',
    'https://meta.icos-cp.eu/collections/WM5ShdLFqPSI0coyVa57G1_Z','https://www.ebi.ac.uk/biosamples/samples/SAMN15743948',
    'https://www.uniprot.org/uniprot/P0CY61','http://doi.org/10.25914/5eaa30de53244','http://tun.fi/JX.1099769','https://ortus.rtu.lv/science/en/datamodule/3',
    'https://databank.ora.ox.ac.uk/UniversityCollege/datasets/04156fde-dabb-48fd-baf6-533182f74b5b', 'https://data.gov.lv/dati/lv/dataset/maksatnespejas-procesi',
    'http://doi.org/10.17882/42182', 'https://repo.clarino.uib.no/xmlui/handle/11509/103', 'https://data.aussda.at/dataset.xhtml?persistentId=doi:10.11587/QQ7HTL',
    'https://meta.icos-cp.eu/collections/WM5ShdLFqPSI0coyVa57G1_Z', 'https://www.ebi.ac.uk/biosamples/samples/SAMN15743948',
    'https://www.uniprot.org/uniprot/P0CY61', 'http://doi.org/10.25914/5eaa30de53244', 'http://gis.ices.dk/geonetwork/srv/eng/catalog.search#/metadata/33fa648d-c4d6-4449-ac3c-dbec0f204e1d',
    'http://id.luomus.fi/GP.110472', 'https://www.ncbi.nlm.nih.gov/nuccore/mh885469','https://doi.org/10.7910/DVN/SI6TUS',
    '0d14fbaa-8cd6-11e7-b2ed-28d244cd6e76','e1b1aee9769d8f401edb6840d9b5f3c8','https://services.fsd.uta.fi/catalogue/FSD3321',
    'https://cera-www.dkrz.de/WDCC/ui/cerasearch/entry?acronym=storm_tide_1906_DWD_reconstruct&exporttype=json-ld', 'https://bolin.su.se/data/cascade-grid',
    'https://doi.org/10.14469/hpc/6215','https://doi.org/10.5880/GFZ.1.1.2020.001','https://doi.org/10.7302/Z24Q7S64','https://chroniclingamerica.loc.gov/lccn/sn90061457/',
    'https://loar.kb.dk/handle/1902/4287','https://qsardb.org/repository/handle/10967/238','https://oai.ukdataservice.ac.uk:8443/oai/provider?verb=GetRecord&metadataPrefix=oai_dc&identifier=10'
    '10.1007/978-981-15-4327-2','10.1051/0004-6361/201525840','10.1109/ICPRIME.2013.6496495',
    '10.1126/science.abe6230','10.11577/1169541','10.11582/2017.00017','10.11583/DTU.10259936.v1',
    '10.11587/I7QIYJ','10.11588/diglit.3135','10.14276/1825-1676.2418','10.14276/1971-8357.2304',
    '10.15129/4051929a-14ed-452c-9a90-8dde26a9fc50','10.15151/ESRF-DC-186933507','10.15152/QDB.115',
    '10.15155/re-69','10.15156/BIO/786344','10.15468/ksqxep','10.1594/WDCC/WRF12_MPIESM_HIST',
    '10.16904/envidat.187','10.17026/dans-xbt-qc5c','10.17043/ao2018-cloud-water','10.17044/scilifelab.13181273',
    '10.17045/sthlmuni.10318046.v1','10.17196/novac.concepcion.001','10.17605/OSF.IO/38U7Q','10.17632/4wpb5rjn76.1',
    '10.17771/PUCRio.ResearchData.51443','10.17862/cranfield.rd.11359613.v5','10.17882/74513','10.17894/ucph.8d941a14-b098-4ca5-b177-412f50be1731',
    '10.18434/T40W22','10.18710/C8JS7L','10.18712/NSD-NSD0991-V1','10.20350/digitalCSIC/8970','10.21334/npolar.2016.3099ea95',
    '10.21994/loar4109','10.22032/dbt.45637','10.22033/ESGF/CMIP6.2450','10.2210/pdb7kn5/pdb','10.23642/usn.7605887.v1',
    '10.23673/re-280','10.23698/aida/ctpa','10.25430/researchdata.cab.unipd.it.00000407','10.25500/edata.bham.00000592',
    '10.25829/bexis.27226-4','0.3109/15368378.2015.1043557','10.3233/JIFS-179079','10.3334/CDIAC/00001_V2013',
    '10.3390/molecules26030683','10.34691/FK2/ULMNHV','10.34848/FK2/8TMRLC','10.34881/1.00001',
    '10.35097/389','10.4225/25/589c57ce5e3d5','10.4232/1.0007','10.5061/dryad.5s0860n','10.5067/38UW2772KQER',
    '10.5067/MODIS/MCD12C1.006','10.5194/hess-22-5817-2018','10.5194/we-20-1-2020','10.5255/UKDA-SN-6721-18',
    '10.5279/DK-SA-DDA-1091','10.5281/zenodo.1493846','10.5286/ISIS.E.RB1900156','10.5445/IR/1000124281',
    '10.5683/SP2/UOHPVH','10.5878/58w0-m352','10.5880/FIDGEO.2021.008','10.6073/pasta/8e9784131971e6d2271ade3d46ecb44f',
    '10.6075/J0513WJD','10.6084/m9.figshare.5375026.v1','10.7265/skbg-kf16','10.7288/V4/MAGIC/17100',
    '10.7483/OPENDATA.V439.NXZC','10.7910/DVN/0PECJC','10037.1/10258','10967/115','11168/11.452917',
    '11304/3d4edfce-39cf-4328-8c28-b623c16c0a48','11495/D9D1-FD1D-3174-1','11509/80','11676/tG1ftg14-_ipJY7UgUTqvVy3',
    '20.500.12115/29','20.5000.1025/ec22a205603a9f2b72e6','20200423-PublicacionesDerivadasDeProyectosFinanciadosPNSD_2001-2019.xlsx',
    '21.11101/0000-0003-3E37-B','21.14100/1d777d08-6ffe-3a8e-a191-bd01476b5345','cgps-streaming.geonet.org.nz:210',
    'doi:10.1002/0470841559.ch1','doi:10.11587/QQ7HTL','doi:10.14459/2021mp1611393','doi:10.1594/PANGAEA.269656','doi:10.1594/WDCC/OceanRAIN-W',
    'doi:10.18710/ABONWP','doi:10.18712/NSD-NSD1360-V1','doi:10.25430/researchdata.cab.unipd.it.00000407','0.34881/BHBSRQ',
    'doi.org/10.14244/198271994149','doi.org/10.17863/CAM.14473','doi.org/10.34881/BHBSRQ','http://b2find.eudat.eu/dataset/ff5ea6b7-7f7a-5c41-a552-96d7c19db32d',
    'http://bibliotecadigitale.cab.unipd.it','http://bio.tools/jaspar','http://catalogo.igme.es/geonetwork/srv/spa/catalog.search#/metadata/ESPIGMEGEODE50Z230020190226',
    'http://catalogo.igme.es/geonetwork/srv/spa/catalog.search#/metadata/ESPIGMEKARST100020200714','http://cdsarc.u-strasbg.fr/viz-bin/cat/J/MNRAS/452/4283',
    'http://data.europa.eu/88u/dataset/covid-19-coronavirus-data-weekly-from-17-december-2020','http://data.windenergy.dtu.dk/controlled-terminology/taxonomy-topics/',
    'http://datadoi.ut.ee/handle/33/47','http://eudat7-devel.dkrz.de/dataset/dfb276d3-eca9-5e93-b22e-90113c0775bd',
    'http://eudat7-devel.dkrz.de/oai?verb=GetRecord&metadataPrefix=oai_b2f&identifier=dfb276d3-eca9-5e93-b22e-90113c0775bd',
    'http://fdp.duchennedatafoundation.org:8080/catalog/874fe107-6c14-4e8a-9984-bd999b8f6df9','http://fel.hi.is/ICENES1999',
    'http://hapi.fhir.org/read?serverId=home_r4&pretty=true&_summary=&resource=Patient&action=read&id=c5fd372f-be03-4630-83db-427e348e11fa&vid=1',
    'http://hdl.handle.net/10067/1541150151162165141','http://hdl.handle.net/10400.20/2089','http://hdl.handle.net/10967/238',
    'http://hdl.handle.net/11234/1-2498','http://hdl.handle.net/11576/2502295','http://hdl.handle.net/20.500.11956/117636',
    'http://id.herb.oulu.fi/GAL.1','http://id.luomus.fi/GP.110472','http://igsn.org/ICDP5054ESYI201',
    'http://jaspar.genereg.net/matrix/MA1631.1/','http://kramerius.cuni.cz/uk/view/uuid:88d83c71-d709-4e7a-adb6-ca76eaf51676?page=uuid:d6833705-15d0-44ae-9772-39b90f3cfa0f',
    'http://lfp.cuni.cz/svi/cze/index.asp','http://libeccio.bo.ismar.cnr.it:8080/geonetwork/srv/ita/catalog.search#/metadata/1d12b137-91e4-4f3b-af1d-a0748c581780',
    'http://nesstar.ics.ul.pt/webview/index.jsp?object=http://nesstar.ics.ul.pt:80/obj/fStudy/APIS0063','http://nesstar.ined.fr/webview/index.jsp?v=2&submode=abstract&study=http%3A%2F%2F10.100.44.41%3A80%2Fobj%2FfStudy%2FIE0215A&mode=documentation&top=yes',
    'http://ontology.deic.dk/rock-n-roll/en/page/Color','http://opendata.cern.ch/record/1','http://proteomecentral.proteomexchange.org/cgi/GetDataset?ID=pxd015947',
    'http://purl.org/net/p-plan','http://purl.org/np/RAwAiO4hKhDUZm5fN-Qwta2ee5X9RJ0F_ebadkFCxipd4','http://qsardb.org/repository/handle/10967/210',
    'http://tun.fi/MZ.intellectualRightsCC-BY-4.0','http://urn.fi/urn:nbn:fi:fsd:T-FSD2084',
    'http://vegbank.org/cite/VB.Ob.15837.INW27055','http://vocab.ciudadesabiertas.es/def/economia/deuda-publica-comercial',
    'http://vocab.nerc.ac.uk/collection/A01/current','http://www.aanda.org/10.1051/0004-6361/201525840',
    'http://www.acervocal.unb.br/acervo/fotografia-24/','http://www.idee.es/csw-codsi-idee/srv/api/records/spaignwms_unidades_administrativas',
    'http://www.kulturarv.dk/ffrepox/OAIHandler?verb=GetRecord&metadataPrefix=ff&identifier=urn:repox.www.kulturarv.dkSites:http://www.kulturarv.dk/fundogfortidsminder/site/351',
    'http://www.lidata.eu/data/quant/LiDA_LVJ_0029','http://www.rohub.org/rodetails/RSOBIA_Ad-1/overview','http://www.vliz.be/en/imis?module=dataset&dasid=5919',
    'https://api.npolar.no/dataset/3099ea95-c3cd-4a8b-af5d-73750e46d791','https://archaeologydataservice.ac.uk/archsearch/record?titleId=1879872',
    'https://archive.ciser.cornell.edu/studies/2854','https://beta.ukdataservice.ac.uk/datacatalogue/studies/study?id=8574',
    'https://bioportal.bioontology.org/ontologies/COGPO','https://bit.ly/BirdsData','https://bolin.su.se/data/zieger-2017',
    'https://catalogue.ceda.ac.uk/uuid/220a65615218d5c9cc9e4785a3234bd0','https://cds.cern.ch/record/423168','https://cera-www.dkrz.de/WDCC/ui/cerasearch/cmip6?input=CMIP6.ScenarioMIP.NOAA-GFDL.GFDL-ESM4',
    'https://ckan-imarine.d4science.org/dataset/code-list-mapping-gears-used-by-iotc-to-the-isscfg-codes57',
    'https://classic.europeana.eu/portal/pt/record/134/S_VGM_object_1M16_100001.html','https://clinicaltrials.gov/ct2/show/NCT03478891',
    'https://comptox.epa.gov/dashboard/dsstoxdb/results?search=DTXSID8021482','https://covid-19.uniprot.org/uniprotkb/P33076',
    'https://cugir.library.cornell.edu/catalog/cugir-007314','https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=973a9333-fec7-46dd-8eb5-25738f06ee54',
    'https://data.aussda.at/dataset.xhtml?persistentId=doi:10.11587/QQ7HTL','https://data.csiro.au/collections/collection/CIcsiro:15473v1',
    'https://data.depositar.io/en/dataset/algae-reef-soundscape','https://data.dtu.dk/articles/dataset/FarmConners_cnblz02e3m_rot00_WakeSteering/13274549',
    'https://data.geus.dk/JupiterWWW/borerapport.jsp?borid=260320','https://data.gov.lv/dati/eng/dataset/iedzivotaju-skaits',
    'https://data.isis.stfc.ac.uk/doi/STUDY/103197058/','https://data.norge.no/datasets/2058f4e4-7fce-4b3f-ad34-34dbf526297d',
    'https://data.npolar.no/dataset/fd4fd3aa-7249-53c9-9846-6e28c5a42587','https://databank.ora.ox.ac.uk/UniversityCollege/datasets/04156fde-dabb-48fd-baf6-533182f74b5b',
    'https://datadoi.ee/handle/33/302','https://datadryad.org/stash/dataset/doi:10.5061/dryad.tf641','https://datasets.aida.medtech4health.se/10.23698/aida/lnco',
    'https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/VWQ5AY','https://dataverse.nl/dataset.xhtml?persistentId=doi:10.34894/PSEZDE','https://dataverse.no/dataset.xhtml?persistentId=doi:10.18710/N8KO4O',
    'https://dataverse.rhi.hi.is/file.xhtml?persistentId=doi:10.34881/K7Y85I/JBSS67','https://dataverse.rsu.lv/dataset.xhtml?persistentId=doi:10.48510/FK2/DNMNBU',
    'https://deepblue.lib.umich.edu/data/concern/data_sets/pz50gw793','https://edoc.hu-berlin.de/handle/18452/22376',
    'https://egdi.geology.cz/record/basic/5006a106-d66c-4916-87bc-91c80a010817','https://hdl.handle.net/11168/11.452068',
    'https://hdl.handle.net/11676/a5Jn7fKEo4dz8f4pKmqrQhPM','https://idata.idiv.de/ddm/Data/ShowData/1880?version=0',
    'https://landregistry.data.gov.uk/data/ppi/transaction-record','https://linked.bodc.ac.uk/sparql/?query=describe+%3Chttp%3A%2F%2Flinked.bodc.ac.uk%2Fseries%2F65425%2F%3E&output=text&stylesheet=',
    'https://linkedsystems.uk/erddap/tabledap/Public_Compressed_RAW_Glider_Data_1112.htmlTable?fileType&distinct()'



]

#testpids=['https://lithologs.net/?action=view&oid=470']
# rdf links:
#testpids=['http://bio2rdf.org/affymetrix:1415765_at','https://www.data.gv.at/katalog/dataset/b8dac7af-5c8a-4936-9abe-e1dbbdd8dd4f','https://identifiers.org/ena.embl:BN000065','https://www.ebi.ac.uk/biosamples/samples/SAMN14168013']
#testpids=['https://data.gov.lv/dati/lv/dataset/covid-19','https://www.data.gouv.fr/datasets/5e7e104ace2080d9162b61d8','https://www.data.gv.at/katalog/dataset/b8dac7af-5c8a-4936-9abe-e1dbbdd8dd4f','https://datos.gob.es/es/catalogo/e05070101-evolucion-de-enfermedad-por-el-coronavirus-covid-19']
#testpids=['https://doi.org/10.26050/WDCC/MOMERGOMBSCMAQ']
#testpids=['https://data.gov.lv/dati/lv/dataset/covid-19']
#ontologies
#testpids=['https://raw.githubusercontent.com/obi-ontology/obi/v2020-04-23/obi.owl']
testpids=['http://vocab.nerc.ac.uk/collection/L22/current/','http://purl.org/vocommons/voaf','http://purl.obolibrary.org/obo/bfo.owl']
#testpids=['http://purl.obolibrary.org/obo/bfo.owl']
#testpids=['https://raw.githubusercontent.com/BFO-ontology/BFO/v2019-08-26/bfo_classes_only.owl']
#testpids=['http://vocab.nerc.ac.uk/collection/L05/current/']
#social sciences
#testpids=['https://doi.org/10.4232/1.13491','http://dx.doi.org/10.18712/NSD-NSD2202-2-v1','http://doi.org/10.5255/UKDA-SN-854270']
#testpids=['https://doi.org/10.1594/PANGAEA.896660']
#testpids=['http://sweetontology.net/matrRockIgneous']
#clarin linguistics
#testpids=['http://hdl.handle.net/20.500.12124/7','http://hdl.handle.net/11495/DAB8-B44B-E8C8-2']
#restricted
#testpids=['https://doi.pangaea.de/10.1594/PANGAEA.919306']
#!!!!!!iana, ddi etc RDF graph, DOI not registered at datacite:
#testpids=['https://doi.org/10.7302/Z24Q7S64']
#testpids=['10.5676/DWD_GPCC/MP_M_V6_100']
#testpids=['10.6092/84cb588d-97e5-4c64-91bb-ba6109dfa530']
#FAIRsFAIR selected repositories
#testpids=['https://doi.org/10.17863/CAM.14473','doi:10.5441/001/1.44cb3946','https://doi.org/10.25704/Z5Y2-QPYE']
#testpids=['https://cera-www.dkrz.de/WDCC/ui/cerasearch/entry?acronym=CMAQ_t_det_w_atmos_tot_N_17']
#testpids=['http://doi.org/10.25914/5eaa30de53244']
# EML by guessed XML
#testpids=['http://dx.doi.org/10.4227/05/5344F1159A1A9']
#testpids=['https://deims.org/dataset/75a7f938-7c77-11e3-8832-005056ab003f']
#testpids=['https://hdl.handle.net/11676/Ok72Hfm8xlJkhg-9lOQpsZGr']
#testpids=['https://data.neonscience.org/data-products/DP1.20066.001']
#not found
#testpids=['https://doi.pangaea.de/10.1594/PANGAEA.920063']
'''
testpids=['https://doi.pangaea.de/10.1594/PANGAEA.896543',
'https://dx.doi.org/10.4227/05/5344F1159A1A9',
'https://doi.org/10.4225/08/563869A931CFE',
'https://data.neonscience.org/data-products/DP1.00001.001',
'https://dx.doi.org/10.11922/sciencedb.293',
'https://deims.org/dataset/75a7f938-7c77-11e3-8832-005056ab003f',
'https://meta.icos-cp.eu/objects/8YwZj8CQEj87IuI9P6QkZiKX',
'http://doi.org/10.22033/ESGF/CMIP6.4397',
'http://doi.org/10.25914/5eaa30de53244']
'''
#DCAT DDI
#testpids=['http://dda.dk/catalogue/150']
#very large file!!
#testpids=['https://doi.org/10.1594/PANGAEA.902845']
#testpids=['https://doi.org/10.1594/PANGAEA.745671']
#testpids=['http://dda.dk/catalogue/150']
#perfect DCAT
#testpids=['https://ckan.govdata.de/ja/dataset/bebauungsplan-rahlstedt-131-hamburgb809f']
#testpids=['https://doi.org/10.1594/PANGAEA.879324']
#testpids=['https://deims.org/dataset/75a7f938-7c77-11e3-8832-005056ab003f','https://hdl.handle.net/11168/11.429265']
#testpids=['https://metadata.bgs.ac.uk/geonetwork/srv/api/records/6abc401d-250a-5469-e054-002128a47908']
#testpids=['https://data.dtu.dk/articles/Data_for_the_paper_A_dual_reporter_system_for_investigating_and_optimizing_translation_and_folding_in_E_coli_/10265420']
#testpids=['https://www.proteinatlas.org/ENSG00000110651-CD81/cell']
#testpids=['http://dda.dk/catalogue/868']
#testpids=['https://ckan.govdata.de/ja/dataset/bebauungsplan-rahlstedt-65-hamburg']
testpids=['https://doi.org/10.1594/PANGAEA.833812']
#testpids=['https://ortus.rtu.lv/science/en/datamodule/294']
#testpids=['https://doi.org/10.15482/USDA.ADC/1324677']
#testpids=['https://www.proteinatlas.org/ENSG00000110651-CD81/cell']
#testpids=['http://doi.org/10.5255/UKDA-SN-1329-1']
#testpids=['http://purl.org/vocommons/voaf']
#testpids=['https://meta.icos-cp.eu/objects/9ri1elaogsTv9LQFLNTfDNXm']
#testpids=['http://doi.org/10.22033/ESGF/CMIP6.4397']
#testpids=['https://su.figshare.com/articles/Data_for_Does_historical_land_use_affect_the_regional_distribution_of_fleshy-fruited_woody_plants_Arnell_et_al_2019_/10318046']
#testpids=['http://doi.org/10.1007/s10531-013-0468-6']
#rdf
testpids=['http://tun.fi/JX.1099769']
#testpids=['https://ortus.rtu.lv/science/en/datamodule/3']
#rdf
#testpids=['https://databank.ora.ox.ac.uk/UniversityCollege/datasets/04156fde-dabb-48fd-baf6-533182f74b5b']
#testpids=['https://data.gov.lv/dati/lv/dataset/maksatnespejas-procesi']

muchotestpids.sort()
testpids = sorted(set(muchotestpids))

#testpids = [testpids[-1]]

#testpids=['https://chroniclingamerica.loc.gov/lccn/sn90061457/']
#testpids=['https://loar.kb.dk/handle/1902/4287']
#testpids=['https://qsardb.org/repository/handle/10967/238']
#testpids=['https://oai.ukdataservice.ac.uk:8443/oai/provider?verb=GetRecord&metadataPrefix=ddi&identifier=10']
#testpids=['http://aceas.tern.org.au/knb/metacat/aceasdata.21/xml']
#testpids=['https://schema.datacite.org/meta/kernel-4.3/example/datacite-example-full-v4.xml']
#testpids=['https://digi.ub.uni-heidelberg.de/diglitData3/mets/uah_m15.xml']
#testpids=['https://digi.ub.uni-heidelberg.de/diglitData3/mets/amalthea.xml']
#testpids=['https://digitalassets.lib.berkeley.edu/techreports/ucb/mets/cuengi_10_1_00025320.xml']
#testpids=['http://ws.pangaea.de/oai/provider?verb=GetRecord&metadataPrefix=iso19139&identifier=oai:pangaea.de:doi:10.1594/PANGAEA.56937']
#testpids=['https://www.geoportal.rlp.de/mapbender/php/mod_inspireAtomFeedISOMetadata.php?id=de11a2ad-57e2-bf20-ccce-5c6ed9ba3920&outputFormat=iso19139&generateFrom=wmslayer&layerid=57335']
#testpids=['https://gdk.gdi-de.org/gdi-de/srv/eng/csw?REQUEST=GetRecords&SERVICE=CSW&VERSION=2.0.2&OUTPUTSCHEMA=http://www.isotc211.org/2005/gmd&constraintLanguage=CQL_TEXT&constraint=ResourceIdentifier=%27https://registry.gdi-de.org/id/de.nw/WUP-GUID_4760800e-baee-482e-8c71-6c0498b5c6df%27&constraint_language_version=1.1.0&typenames=csw:Record&resulttype=results&elementsetname=full#xpointer(//gmd:identificationInfo[1]/gmd:MD_DataIdentification)']
#testpids=['https://services.data.shom.fr/geonetwork/srv/api/records/412878/formatters/xml']
#testpids=['http://data.aims.gov.au/resources/mest/reefstate.xml']
#testpids=['http://marine-analyst.eu/metadata/WIND_GLO_WIND_L4_NRT_OBSERVATIONS_012_004.xml']
#testpids=['https://doi.org/10.1594/PANGAEA.893199']
startpid='https://www.proteinatlas.org/ENSG00000110651-CD81/cell'
metadata_service_endpoint = ''
metadata_service_type = 'oai_pmh'
oaipmh_endpoint = ''
def effectivehandlers(logger):
    handlers = logger.handlers
    while True:
        logger = logger.parent
        handlers.extend(logger.handlers)
        if not (logger.parent and logger.propagate):
            break
    return handlers
def main():
    config = ConfigParser.ConfigParser()
    my_path = Path(__file__).parent.parent
    ini_path = os.path.join(my_path,'config','server.ini')
    config.read(ini_path)
    YAML_DIR = config['SERVICE']['yaml_directory']
    METRIC_YAML = config['SERVICE']['metrics_yaml']
    METRIC_YML_PATH = os.path.join(my_path, YAML_DIR , METRIC_YAML)
    SPDX_URL = config['EXTERNAL']['spdx_license_github']
    DATACITE_API_REPO = config['EXTERNAL']['datacite_api_repo']
    RE3DATA_API = config['EXTERNAL']['re3data_api']
    METADATACATALOG_API = config['EXTERNAL']['metadata_catalog']
    isDebug = config.getboolean('SERVICE', 'debug_mode')
    data_files_limit = int(config['SERVICE']['data_files_limit'])
    metric_specification = config['SERVICE']['metric_specification']
    remote_log_host = config['SERVICE']['remote_log_host']
    remote_log_path = config['SERVICE']['remote_log_path']

    preproc = Preprocessor()
    preproc.retrieve_metrics_yaml(METRIC_YML_PATH, data_files_limit,metric_specification)
    print('Total metrics defined: {}'.format(preproc.get_total_metrics()))

    isDebug = config.getboolean('SERVICE', 'debug_mode')
    preproc.retrieve_licenses(SPDX_URL, isDebug)
    preproc.retrieve_datacite_re3repos(RE3DATA_API, DATACITE_API_REPO, isDebug)
    preproc.retrieve_metadata_standards(METADATACATALOG_API, isDebug)
    preproc.retrieve_science_file_formats(isDebug)
    preproc.retrieve_long_term_file_formats(isDebug)

    print('Total SPDX licenses : {}'.format(preproc.get_total_licenses()))
    print('Total re3repositories found from datacite api : {}'.format(len(preproc.getRE3repositories())))
    print('Total subjects area of imported metadata standards : {}'.format(len(preproc.metadata_standards)))
    start=False
    usedatacite = True
    #tracemalloc.start()
    n=1
    for identifier in testpids:

        print (identifier)
        print(n)
        n+=1
        if identifier==startpid or not startpid:
            start=True
        if start:
            ft = FAIRCheck(uid=identifier, test_debug=debug, metadata_service_url=metadata_service_endpoint,
                           metadata_service_type=metadata_service_type, use_datacite=usedatacite, oaipmh_endpoint=oaipmh_endpoint)

            #ft = FAIRCheck(uid=identifier,  test_debug=True, use_datacite=usedatacite)
            #set target for remote logging
            if remote_log_host and remote_log_path:
                ft.set_remote_logging_target(remote_log_host, remote_log_path)

            uid_result, pid_result = ft.check_unique_persistent()
            ft.retrieve_metadata_embedded(ft.extruct_result)
            include_embedded= True
            if ft.repeat_pid_check:
                uid_result, pid_result = ft.check_unique_persistent()
            ft.retrieve_metadata_external()
            if ft.repeat_pid_check:
                uid_result, pid_result = ft.check_unique_persistent()
            core_metadata_result = ft.check_minimal_metatadata()
            content_identifier_included_result = ft.check_content_identifier_included()
            access_level_result=ft.check_data_access_level()
            license_result = ft.check_license()
            relatedresources_result = ft.check_relatedresources()
            check_searchable_result = ft.check_searchable()
            data_content_metadata = ft.check_data_content_metadata()
            data_file_format_result=ft.check_data_file_format()
            community_standards_result=ft.check_community_metadatastandards()
            data_provenance_result=ft.check_data_provenance()
            formal_representation_result=ft.check_formal_metadata()
            semantic_vocabulary_result =ft.check_semantic_vocabulary()
            metadata_preserved_result = ft.check_metadata_preservation()
            standard_protocol_metadata_result = ft.check_standardised_protocol_metadata()
            standard_protocol_data_result = ft.check_standardised_protocol_data()
            results = [uid_result, pid_result, core_metadata_result, content_identifier_included_result, check_searchable_result, access_level_result, formal_representation_result,semantic_vocabulary_result, license_result, data_file_format_result,data_provenance_result,relatedresources_result,community_standards_result,data_content_metadata,metadata_preserved_result, standard_protocol_data_result,standard_protocol_metadata_result]
            #print(ft.metadata_merged)
            debug_messages = ft.get_log_messages_dict()
            ft.logger_message_stream.flush()
            summary = ft.get_assessment_summary(results)
            #print('summary: ', summary)
            for res_k, res_v in enumerate(results):
                if ft.isDebug:
                    debug_list = debug_messages.get(res_v['metric_identifier'])
                    #debug_list= ft.msg_filter.getMessage(res_v['metric_identifier'])
                    if debug_list is not None:
                        results[res_k]['test_debug'] = debug_messages.get(res_v['metric_identifier'])
                    else:
                        results[res_k]['test_debug'] =['INFO: No debug messages received']
                else:
                    results[res_k]['test_debug'] = ['INFO: Debugging disabled']
                    debug_messages = {}
           # print(json.dumps(results, indent=4, sort_keys=True))
            print(json.dumps([core_metadata_result,check_searchable_result], indent=4, sort_keys=True))
            #remove unused logger handlers and filters to avoid memory leaks
            ft.logger.handlers = [ft.logger.handlers[-1]]
            #ft.logger.filters = [ft.logger.filters]
            #current, peak = tracemalloc.get_traced_memory()
            #print(f"Current memory usage is {current / 10 ** 6}MB; Peak was {peak / 10 ** 6}MB")
            #snapshot = tracemalloc.take_snapshot()
            #top_stats = snapshot.statistics('traceback')

            # pick the biggest memory block
            #stat = top_stats[0]
            #print("%s memory blocks: %.1f KiB" % (stat.count, stat.size / 1024))
            #for line in stat.traceback.format():
            #    print(line)

            #for i, stat in enumerate(snapshot.statistics('filename')[:5], 1):
            #    print(i,  str(stat))

            #preproc.logger.
            gc.collect()
    #tracemalloc.stop()
if __name__ == '__main__':
    main()
