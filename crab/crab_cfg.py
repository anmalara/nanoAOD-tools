
from WMCore.Configuration import Configuration
from CRABClient.UserUtilities import config

import md5
import sys
import re

def get_dataset():
    # Parse dataset from commandline
    # Stolen from https://gitlab.cern.ch/nsmith/monoZ/blob/master/crab/crab.py
    dataset = 'dummy'
    for arg in sys.argv:
        if 'Data.inputDataset=' in arg:
            dataset = arg.split('=')[1]
    if dataset == 'dummy':
        raise Exception("Must pass dataset argument as Data.inputDataset=...")
    return dataset


def base_configuration():
    config = Configuration()

    config.section_("General")
    config.General.transferLogs=True
    config.section_("JobType")
    config.JobType.pluginName = 'Analysis'
    config.JobType.psetName = 'PSet.py'
    config.JobType.scriptExe = 'crab_script.sh'
    config.JobType.inputFiles = ['../scripts/haddnano.py'] #hadd nano will not be needed once nano tools are in cmssw
    config.JobType.sendPythonFolder	 = True
    config.JobType.maxJobRuntimeMin	 = 2400
    config.section_("Data")
    config.Data.inputDBS = 'global'
    config.Data.splitting = 'FileBased'
    config.Data.unitsPerJob = 1
    # config.Data.totalUnits = 10

    config.Data.publication = False


    return config

# Ensure that the string is not longer than 100 characters
# To comply with the CRAB request name limit
def cut_string(string_in):
    l = len(string_in)
    if l < 100:
        return string_in

    partial_hash = md5.md5(string_in[90:]).hexdigest()
    ret = string_in[:90] + partial_hash[:10]
    return ret

def short_name(dataset):
    _, name, conditions, _ = dataset.split("/")

    # Remove useless info
    name = name.replace("_TuneCP5","")
    name = name.replace("_TuneCUETP8M1","")
    name = name.replace("_13TeV","")
    name = name.replace("-pythia8","")
    name = name.replace("madgraphMLM","MLM")
    name = name.replace("madgraph","mg")
    name = name.replace("amcnloFXFX","FXFX")
    name = name.replace("powheg","pow")

    # Detect extension
    m=re.match(r".*(ext\d+).*",conditions)
    if m:
        name = name + "_" + m.groups()[0]
    m=re.match(r".*(ver\d+).*",conditions)
    if m:
        name = name + "_" + m.groups()[0]
    if 'new_pmx' in conditions:
        name = name + '_new_pmx'
    if ('RunIISummer16' in conditions) or ("UL16" in conditions):
        name = name + "_2016"
    elif ("RunIIFall17" in conditions) or ("UL17" in conditions):
        name = name + "_2017"
    elif ('RunIIAutumn18' in conditions) or ("UL18" in conditions):
        name = name + "_2018"

    m = re.match(r"Run(\d+[A-Z]*)", conditions)
    if m:
        run = m.groups()[0]

        m = re.match(".*-v(\d+)", conditions)
        if m:
            name = name + "_ver{0}".format(m.groups()[0])
        
        name = name + "_" + run
    return name

# Define the tag for this submission
tag = "PFNANO_03Feb23_v2_PostNanoTools"
dataset = get_dataset()
name = short_name(dataset)
config = base_configuration()


### Determine what to do based on type of dataset
is_mc = dataset.endswith("SIM") or "13TeV" in dataset
crab_script = "crab_script_monojet.py"


if ("Summer16" in dataset) or ("Run2016" in dataset):
    year=2016
elif ("Run2017" in dataset) or ("Fall17" in dataset) or ("UL17" in dataset):
    year=2017
if ("Autumn18" in dataset) or ("Run2018" in dataset) or ("UL18" in dataset):
    year=2018

if not is_mc:
    if year==2016:
        config.JobType.inputFiles.append("input/json/Cert_271036-284044_13TeV_ReReco_07Aug2017_Collisions16_JSON.txt")
    elif year==2017:
        config.JobType.inputFiles.append("input/json/Cert_294927-306462_13TeV_EOY2017ReReco_Collisions17_JSON_v1.txt")
    elif year==2018:
        config.JobType.inputFiles.append("input/json/Cert_314472-325175_13TeV_17SeptEarlyReReco2018ABC_PromptEraD_Collisions18_JSON.txt")

config.JobType.inputFiles.append(crab_script)
config.JobType.inputFiles.append('keep_and_drop_monojet.txt')

# Pass the dataset name as an argument so that
# the script can write it into the output files.
config.JobType.scriptArgs = ["dataset={}".format(name),
                             "ismc={}".format(is_mc),
                             "year={}".format(year)]
if 'sync' in tag:
    config.JobType.scriptArgs.append("nofilter=true")

config.General.requestName = cut_string(name)
config.Data.inputDataset = dataset

if "test" in tag:
    config.Data.totalUnits = 1
else:
    config.Data.totalUnits = -1

config.Data.outputDatasetTag = name

# Look at phys03 DB for custom PFNANO samples
if dataset.endswith("USER"):
    config.Data.inputDBS = "phys03"

config.section_("Site")

import socket
host = socket.gethostname()
if 'lxplus' in host:
    config.Site.storageSite = "T2_CH_CERN"
    config.Data.outLFNDirBase = '/store/group/phys_higgs/vbfhiggs/{0}/'.format(tag)
elif 'lpc' in host:
    config.Site.storageSite = "T3_US_FNALLPC"
    config.Data.outLFNDirBase = '/store/user/aakpinar/nanopost/{0}/'.format(tag)
else:
    raise RuntimeError("Cannot parse hostname: " + host)

config.General.workArea = "./wdir/{}".format(tag)
config.JobType.allowUndistributedCMSSW = True
