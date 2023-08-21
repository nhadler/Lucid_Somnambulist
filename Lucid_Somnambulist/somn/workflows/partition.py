import molli as ml
from somn.workflows.firstgen_calc_sub import main as calc_sub
from somn.calculate import preprocess
from somn.build.assemble import (
    # load_calculated_substrate_descriptors,
    assemble_descriptors_from_handles,
    # assemble_random_descriptors_from_handles,
)
import os

# from somn.workflows import PART_, DESC_
from somn.util.project import Project
from copy import deepcopy
from glob import glob

# Load in raw calculated descriptors + random descriptors


def main(
    val_schema="", vt=None, mask_substrates=True, rand=False, serialize_rand=False
):
    """
    Validation Schema Argument (val_schema):

    validation or test are abbreviated "v" or "t"
    in-sample and out-of-sample are abbreviate "i" and "o"

    val in, test out (or test out, val in) would be "vi_to" or "to_vi"

    NOTE: if not running a random feature control, leave "rand" as False. This will save on space.
    Turn this on if interested in testing the efficacy of descriptors.

    For substrate masking, the boolean argument is being passed to a few functions down. The assemble_*_descriptors_from_handles function will handle it.

    """
    assert bool(
        set([val_schema])
        & set(["to_vi", "vi_to", "random", "vo_to", "to_vo", "noval_to", "to_noval"])
    )
    if mask_substrates == True:
        import pandas as pd

        am_mask = pd.read_csv(
            f"{Project().descriptors}/amine_mask.csv", header=0, index_col=0
        )
        br_mask = pd.read_csv(
            f"{Project().descriptors}/bromide_mask.csv", header=0, index_col=0
        )
        sub_mask = (am_mask, br_mask)
        # print("DEBUG",sub_mask[0], sub_mask[0]["0"], type(sub_mask[0]))
    else:
        sub_mask = None
    if val_schema == "vo_to" or val_schema == "to_vo":
        import random

        for i, val in enumerate(unique_couplings):
            am, br = val.split("_")  # The test reactants
            nn_val_sub = random.sample(
                [f for f in combos if f != val and f[0] != am and f[1] != br], 3
            )  # sample three different validation pairs from random combinations that are NOT the test coupling OR either reactant for test
            v_am = []
            v_br = []
            for val_sub in nn_val_sub:  # get list of amines and bromides for validation
                am_, br_ = val_sub.split("_")
                v_am.append(am_)
                v_br.append(br_)
            name_ = (
                str(i + 1)
                + "_te_"
                + f"a{am}_b{br}"
                + "_v_"
                + "_".join(["a" + f for f in v_am])
                + "_"
                + "_".join(["b" + f for f in v_br])
            )
            outsamp_test_handles = preprocess.split_outsamp_reacts(
                dataset, amines=[am], bromides=[br], separate=False
            )
            outsamp_val_handles_contam = preprocess.split_outsamp_reacts(
                dataset, amines=v_am, bromides=v_br, separate=False
            )  # This will sometimes be contaminated by couplings with validation reactants and one of the test reactants
            outsamp_val_handles = [
                f for f in outsamp_val_handles_contam if f not in outsamp_test_handles
            ]  # This explicitly removes ANY match with a test set reaction
            tr_int, te = preprocess.outsamp_by_handle(dataset, outsamp_test_handles)
            tr, va = preprocess.outsamp_by_handle(tr_int, outsamp_val_handles)
            partition_pipeline_val(
                name_,
                tr,
                va,
                te,
                vt=vt,
                sub_mask=sub_mask,
                rand=rand,
                serialize_rand=serialize_rand,
            )
            # ### DEBUG
            # if i == 4:
            #     break
    elif val_schema == "noval_to" or val_schema == "to_noval":
        for i, val in enumerate(combos):
            am, br = val.split("_")
            name_ = str(i + 1) + "_" + val + "_"
            outsamp_handles = preprocess.split_outsamp_reacts(
                dataset, amines=[am], bromides=[br], separate=False
            )
            tr, te = preprocess.outsamp_by_handle(dataset, outsamp_handles)
            tr, va = preprocess.random_splits(
                tr, validation=False, n_splits=1, fold=7
            )  # Comment out to only do train/test
            ### DEV ###
            raise Exception("Under development")
    else:
        for i, val in enumerate(combos):
            am, br = val.split("_")
            name_ = str(i + 1) + "_" + val + "_" + val_schema + "-schema"
            if val_schema == "random":
                ### RANDOM SPLITS ###
                tr, va, te = preprocess.random_splits(dataset, validation=True, fold=10)
            ### OUT OF SAMPLE TEST, IN SAMPLE VAL ###
            # am_f,br_f,both,outsamp_handles = split_outsamp_reacts(data_df,amines=[44,38,32],bromides=[13],separate=True)
            elif val_schema == "to_vi" or val_schema == "vi_to":
                outsamp_handles = preprocess.split_outsamp_reacts(
                    dataset, amines=[am], bromides=[br], separate=False
                )
                # tr,va,te,valm,testm = preprocess.platewise_splits(dataset,num_coup=5,save_mask=True,val_int=False,val_split=8,test_list=[uni_coup[i]])
                temp, te = preprocess.outsamp_by_handle(dataset, outsamp_handles)
                tr, va = preprocess.random_splits(
                    temp, validation=False, n_splits=1, fold=7
                )
            #### DEV
            if 65 < i < 73:  # Actually run these
                pass
            else:
                continue  # Skip others
            #### DEV
            partition_pipeline_val(
                name_,
                tr,
                va,
                te,
                vt=vt,
                sub_mask=sub_mask,
                rand=rand,
                serialize_rand=serialize_rand,
            )
            #### DEBUG
            # if i == 4:
            # break


def partition_pipeline_noval(
    name_, tr, te, vt=None, rand=True, sub_mask=False, serialize_rand=False
):
    """
    Partition pipeline, but for models with no validation set
    """
    x_tr = assemble_descriptors_from_handles(tr.index.tolist(), rand, sub_mask=sub_mask)
    x_te = assemble_descriptors_from_handles(te.index.tolist(), rand, sub_mask=sub_mask)
    x_tr_real = assemble_descriptors_from_handles(
        tr.index.tolist(), sub_am_dict, sub_br_dict, sub_mask=sub_mask
    )
    x_te_real = assemble_descriptors_from_handles(
        te.index.tolist(), sub_am_dict, sub_br_dict, sub_mask=sub_mask
    )
    (x_tr_, x_te_), (
        x_tr_re,
        x_te_re,
    ) = preprocess.new_mask_random_feature_arrays(
        (x_tr_real, x_te_real), (x_tr, x_te), _vt=vt
    )  # Use this for only train/test
    if serialize_rand == True:
        x_tr_.to_feather(randout + name_ + "_xtr.feather")
        x_te_.to_feather(randout + name_ + "_xte.feather")
        tr.transpose().reset_index(drop=True).to_feather(
            randout + name_ + "_ytr.feather"
        )
        te.transpose().reset_index(drop=True).to_feather(
            randout + name_ + "_yte.feather"
        )
    x_tr_re.to_feather(realout + name_ + "_xtr.feather")
    x_te_re.to_feather(realout + name_ + "_xte.feather")
    tr.transpose().reset_index(drop=True).to_feather(realout + name_ + "_ytr.feather")
    te.transpose().reset_index(drop=True).to_feather(realout + name_ + "_yte.feather")


def partition_pipeline_val(
    name_, tr, va, te, vt=None, rand=False, sub_mask=False, serialize_rand=False
):
    """
    NOTE: sub_mask is passed on to vectorize_substrate_descriptors, and must be a tuple of length 2, with (amine,bromide) masks. Can be pd.Series, pd.DataFrame (with a column "0"), or a numpy array of boolean values.
    """
    if isinstance(rand, tuple):
        x_tr = assemble_descriptors_from_handles(
            tr.index.tolist(), rand, sub_mask=sub_mask
        )
        x_va = assemble_descriptors_from_handles(
            va.index.tolist(), rand, sub_mask=sub_mask
        )
        x_te = assemble_descriptors_from_handles(
            te.index.tolist(), rand, sub_mask=sub_mask
        )
    else:  ### DEV - need to change this
        raise Exception(
            "Must pass random descriptors to partition pipeline function - this is going to be depreciated later"
        )
    # Real features used to generate masks for random features
    x_tr_real = assemble_descriptors_from_handles(
        tr.index.tolist(), real, sub_mask=sub_mask
    )
    x_va_real = assemble_descriptors_from_handles(
        va.index.tolist(), real, sub_mask=sub_mask
    )
    x_te_real = assemble_descriptors_from_handles(
        te.index.tolist(), real, sub_mask=sub_mask
    )
    (x_tr_, x_va_, x_te_), (
        x_tr_re,
        x_va_re,
        x_te_re,
    ) = preprocess.new_mask_random_feature_arrays(
        (x_tr_real, x_va_real, x_te_real), (x_tr, x_va, x_te), _vt=vt
    )
    if serialize_rand == True:
        ### Rand copies of X
        x_tr_.to_feather(randout + name_ + "_rand-feat_xtr.feather")
        x_va_.to_feather(randout + name_ + "_rand-feat_xva.feather")
        x_te_.to_feather(randout + name_ + "_rand-feat_xte.feather")
        ### "Rand" copies of Y
        ############ NOTE: the y-values do not change with random features - so we're just serializing two copies for each set here for convenience. They are small. ####
        tr.transpose().reset_index(drop=True).to_feather(
            randout + name_ + "_rand-feat_ytr.feather"
        )
        va.transpose().reset_index(drop=True).to_feather(
            randout + name_ + "_rand-feat_yva.feather"
        )
        te.transpose().reset_index(drop=True).to_feather(
            randout + name_ + "_rand-feat_yte.feather"
        )
    x_tr_re.to_feather(realout + name_ + "_real-feat_xtr.feather")
    x_va_re.to_feather(realout + name_ + "_real-feat_xva.feather")
    x_te_re.to_feather(realout + name_ + "_real-feat_xte.feather")
    tr.transpose().reset_index(drop=True).to_feather(
        realout + name_ + "_real-feat_ytr.feather"
    )
    va.transpose().reset_index(drop=True).to_feather(
        realout + name_ + "_real-feat_yva.feather"
    )
    te.transpose().reset_index(drop=True).to_feather(
        realout + name_ + "_real-feat_yte.feather"
    )


def check_sub_status():
    """
    Helper function to check if substrates have been calculated.
    """
    project = Project()
    k = glob(f"{project.descriptors}/real_*_desc_*.p")
    if len(k) == 2:
        return True
    elif len(k) == 1:
        raise Exception("Substrate descriptors are being mixed up -- DEBUG")
    elif len(k) == 0:
        return False
    else:
        raise Exception(
            "DEBUG - inappropriate number of files in DESC_ directory that look like substrate descriptor files"
        )


def fetch_precalc_sub_desc():
    """
    Fetch precalculated descriptors (after checking if they are done).
    """
    project = Project()
    amine = glob(f"{project.descriptors}/real_amine_desc_*.p")
    bromide = glob(f"{project.descriptors}/real_bromide_desc_*.p")
    random = f"{project.descriptors}/random_am_br_cat_solv_base.p"
    return amine, bromide, random


def get_precalc_sub_desc():
    """
    Check status, then load descriptors if they are precalculated
    """
    status = check_sub_status()
    if status == True:  # Already calculated
        amf, brf, rand_fp = fetch_precalc_sub_desc()
        import pickle

        assert len(amf) == 1 & len(brf) == 1
        sub_am_dict = pickle.load(open(amf[0], "rb"))
        sub_br_dict = pickle.load(open(brf[0], "rb"))
        with open(rand_fp, "rb") as k:
            rand = pickle.load(k)
        real = (sub_am_dict, sub_br_dict, cat_desc, solv_desc, base_desc)
        return real, rand
    else:
        return False


if __name__ == "__main__":
    from sys import argv

    if argv[1] == "new":
        assert len(argv) >= 3
        project = Project()
        project.save(identifier=argv[2])
    else:
        try:
            project = Project.reload(how=argv[1])
        except:
            raise Exception(
                "Must pass valid identifier or 'last' to load project. Can say 'new' and give an identifier"
            )

    # project = Project() ## DEBUG
    (
        amines,
        bromides,
        dataset,
        handles,
        unique_couplings,
        a_prop,
        br_prop,
        base_desc,
        solv_desc,
        cat_desc,
    ) = preprocess.load_data(optional_load="maxdiff_catalyst")

    # Checking project status to make sure sub descriptors are calculated
    sub_desc = get_precalc_sub_desc()
    if sub_desc == False:  # Need to calculate
        real, rand = calc_sub(
            project, optional_load="maxdiff_catalyst", substrate_pre=("corr", 0.90)
        )
    else:
        real, rand = sub_desc

    sub_am_dict, sub_br_dict, cat_desc, solv_desc, base_desc = real
    print(rand)
    # Val have out of sample reactants
    # combos = preprocess.get_all_combos(unique_couplings)
    combos = deepcopy(
        unique_couplings
    )  # This will significantly cut down on the number of partitions
    import pandas as pd

    # print(pd.DataFrame(combos).to_string())
    outdir = deepcopy(f"{project.partitions}/")
    os.makedirs(outdir + "real/", exist_ok=True)
    os.makedirs(outdir + "rand/", exist_ok=True)
    realout = outdir + "real/"
    randout = outdir + "rand/"

    main(
        val_schema="vi_to", vt=0, mask_substrates=True, rand=rand, serialize_rand=False
    )  ## Correlation cutoff is under development: should not be implemented here.
