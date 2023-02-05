#!/usr/bin/env python
import os
import sys
import re
from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import *

#this takes care of converting the input files from CRAB
from PhysicsTools.NanoAODTools.postprocessing.framework.crabhelper import inputFiles,runsAndLumis, addDatasetTag

from PhysicsTools.NanoAODTools.postprocessing.modules.common.puWeightProducer import *
from PhysicsTools.NanoAODTools.postprocessing.modules.monojet.monojetpost import monojetPost, variation_safe_pt_cut
from PhysicsTools.NanoAODTools.postprocessing.modules.monojet.triggerselector import triggerSelector

from PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetmetUncertainties import *
from PhysicsTools.NanoAODTools.postprocessing.modules.common.PrefireCorr import PrefCorr
from PhysicsTools.NanoAODTools.postprocessing.modules.common.collectionMerger import collectionMerger
from PhysicsTools.NanoAODTools.postprocessing.modules.common.puWeightProducer import puAutoWeight_2016, puAutoWeight_2017, puAutoWeight_2018
from PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetmetHelperRun2 import createJMECorrector

import PSet

def filter_electrons(electron):
    return (electron.pt>9.9) and (electron.cutBased > 0)

def filter_photons(photon):
    if hasattr(photon, 'cutBasedBitmap'):
        return photon.cutBasedBitmap > 0
    if hasattr(photon, 'cutBased17Bitmap'):
        return photon.cutBased17Bitmap > 0
    return False

def filter_genpart(genpart):
    good = False
    good |= genpart.status in [1,2,62]
    good |= (abs(genpart.pdgId) in [11,12,13,14,15,16,22,23,24])
    return good

def extract_period(dataset):
    m = re.match('.*201\d([A-Z])', dataset)
    if not m:
        raise RuntimeError("Could not extract run period from dataset: " + dataset)
    return m.groups()[0]

def filter_muons(muon):
    return (muon.pt>9.9) and (muon.looseId) and (muon.pfRelIso04_all < 0.4)

def met_branch_name(year, jet_type, ulegacy=True):
    if (year == '2017') and (jet_type=='AK4PFchs'):
        if ulegacy:
            return "MET"
        else:
            return "METFixEE2017"
    else:
        return "MET"

jsons = {
        '2016': "Cert_271036-284044_13TeV_ReReco_07Aug2017_Collisions16_JSON.txt",
        '2017': "Cert_294927-306462_13TeV_EOY2017ReReco_Collisions17_JSON_v1.txt",
        '2018': "Cert_314472-325175_13TeV_17SeptEarlyReReco2018ABC_PromptEraD_Collisions18_JSON.txt"
}

def read_options():
    # Loop over input arguments
    options = {}
    prefixes = ['dataset', 'ismc', 'year','nofilter','test','file','nocrab']
    for argument in sys.argv:
        for prefix in prefixes:
            if argument.startswith(prefix):
                value = argument.split('=')[-1]
                options[prefix] = value
    for p in prefixes:
        if p not in options.keys():
            options[p] = ''

    options['ismc'] = options['ismc'].lower() == "true"
    options['nofilter'] = options['nofilter'].lower() == "true"
    options['test'] = options['test'].lower() == "true"
    options['nocrab'] = options['nocrab'].lower() == "true"

    return options

def main():
    options = read_options()

    if options['test']:
        files = [options['file']]
        maxEntries = 1000
    elif options['nocrab']:
        files = [x for x in sys.argv if x.endswith(".root")]
        maxEntries = 0
    else:
        files = inputFiles()
        maxEntries = 0
    branchsel = "keep_and_drop_monojet.txt"

    if options['nofilter']:
        selectors = []
        mc_selectors = []
    else:
        if options['year'] == '2016' and not options['ismc']:
            jetsorter = lambda x: x.pt
        else:
            jetsorter = lambda x: x.pt_nom
        
        # We'll sort PF candidates by their pt
        pfcandsorter = lambda x: x.pt

        # Sort AK4 and AK8 jets by their pt
        # Also sort PF candidates by their pt, and take the first 500 (max)
        selectors = [
            # collectionMerger(input=["Jet"],output="Jet", selector={"Jet" : lambda x : variation_safe_pt_cut(x,19.9)}),
            # collectionMerger(input=["FatJet"],output="FatJet", selector={"FatJet" : lambda x : variation_safe_pt_cut(x,150.0)}),
            # collectionMerger(input=["Muon"],output="Muon", selector={"Muon" : filter_muons}),
            # collectionMerger(input=["Electron"],output="Electron", selector={"Electron" : filter_electrons}),
            # collectionMerger(input=["Photon"],output="Photon", selector={"Photon" : filter_photons}),
            collectionMerger(input=["Jet"],output="Jet",sortkey=jetsorter),
            collectionMerger(input=["FatJet"],output="FatJet",sortkey=jetsorter),
            collectionMerger(input=["PFCand"],output="PFCand",sortkey=pfcandsorter, maxObjects=500),
        ]

        # Selections on GEN jets and particles
        mc_selectors = [
            collectionMerger(input=["GenPart"],output="GenPart", selector={"GenPart" : filter_genpart}),
            collectionMerger(input=["GenJet"],output="GenJet", selector={"GenJet" : lambda x : x.pt>20}),
            collectionMerger(input=["GenJetAK8"],output="GenJetAK8", selector={"GenJetAK8" : lambda x : x.pt>20})
        ]

    if options['ismc']:
        jme_modules = []
        for jet_type in ['AK4PFchs', 'AK8PFPuppi']:
            jme_modules.append(
                               createJMECorrector(
                                                  isMC=True,
                                                  dataYear=options['year'],
                                                  jesUncert="Total",
                                                  jetType=jet_type,
                                                  metBranchName=met_branch_name(options['year'], jet_type),
                                                  isUL=True
                                                  )()
                                )
        if options['year'] == '2016':
            pu_modules = [puAutoWeight_2016()]
            pref_modules = [
                            PrefCorr(
                                    jetroot="L1prefiring_jetpt_2016BtoH.root",
                                    jetmapname="L1prefiring_jetpt_2016BtoH",
                                    photonroot="L1prefiring_photonpt_2016BtoH.root",
                                    photonmapname="L1prefiring_photonpt_2016BtoH",
                                    branchnames=["PrefireWeight","PrefireWeight_Up", "PrefireWeight_Down"]
                                    ),
                            PrefCorr(
                                    jetroot="L1prefiring_jetempt_2016BtoH.root",
                                    jetmapname="L1prefiring_jetempt_2016BtoH",
                                    photonroot="L1prefiring_photonpt_2016BtoH.root",
                                    photonmapname="L1prefiring_photonpt_2016BtoH",
                                    branchnames=["PrefireWeight_jetem","PrefireWeight_jetem_Up", "PrefireWeight_jetem_Down"]
                                    )
                            ]
        if options['year'] == '2017':
            pu_modules = [ puAutoWeight_2017() ]
            pref_modules = [
                            PrefCorr(
                                    jetroot="L1PrefiringMaps_UL.root",
                                    jetmapname="L1prefiring_jetptvseta_UL2017BtoF",
                                    photonroot="L1PrefiringMaps_UL.root",
                                    photonmapname="L1prefiring_photonptvseta_UL2017BtoF",
                                    branchnames=["PrefireWeight","PrefireWeight_Up", "PrefireWeight_Down"]
                                    ),
                            PrefCorr(
                                    jetroot="L1PrefiringMaps_UL.root",
                                    jetmapname="L1prefiring_jetemptvseta_UL2017BtoF",
                                    photonroot="L1PrefiringMaps_UL.root",
                                    photonmapname="L1prefiring_photonptvseta_UL2017BtoF",
                                    branchnames=["PrefireWeight_jetem","PrefireWeight_jetem_Up", "PrefireWeight_jetem_Down"]
                                    )
                            ]
        elif options['year'] == '2018':
            pu_modules = [ puAutoWeight_2018() ]
            pref_modules = []

        modules = jme_modules + pu_modules + pref_modules + selectors + mc_selectors
        p = PostProcessor(
            outputDir=".",
            inputFiles=files,
            outputbranchsel=branchsel,
            modules=modules,
            provenance=True,
            maxEntries=maxEntries,
            fwkJobReport=True)
    else:
        jme_modules = []
        if options['year']=='2018' or options['year']=='2017':
            run_period = extract_period(options['dataset'])
            for jet_type in ['AK4PFchs', 'AK8PFPuppi']:
                jme_modules.append(
                                createJMECorrector(
                                                    isMC=False,
                                                    dataYear=options['year'],
                                                    jesUncert="Total",
                                                    runPeriod=run_period,
                                                    jetType=jet_type,
                                                    metBranchName=met_branch_name(options['year'], jet_type),
                                                    isUL=True
                                                    )()
                                    )

        modules = jme_modules + selectors
        p=PostProcessor(outputDir=".",
            inputFiles=files,
            outputbranchsel=branchsel,
            modules=modules,
            provenance=True,
            fwkJobReport=True,
            maxEntries=maxEntries,
            jsonInput=jsons[options['year']])
    p.run()

    addDatasetTag()

    print "DONE"

if __name__ == "__main__":
    main()

