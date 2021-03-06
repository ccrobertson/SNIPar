#!/well/kong/users/wiw765/anaconda2/bin/python
import numpy as np
import numpy.ma as ma
from pysnptools.snpreader import Bed, Pheno
from scipy.stats import zscore
from sibreg import sibreg
import h5py, argparse

def read_covariates(covar_file,ids_to_match,missing):
## Read a covariate file and reorder to match ids_to_match ##
    # Read covariate file
    covar_f = Pheno(covar_file, missing=missing).read()
    ids = covar_f.iid
    # Get covariate values
    n_X=covar_f._col.shape[0]+1
    X=np.ones((covar_f.val.shape[0],n_X))
    X[:, 1:n_X] = covar_f.val
    # Get covariate names
    X_names = np.zeros((n_X), dtype='S10')
    X_names[0] = 'Intercept'
    X_names[1:n_X] = np.array(covar_f._col, dtype='S20')
    # Remove NAs
    NA_rows = np.isnan(X).any(axis=1)
    n_NA_row = np.sum(NA_rows)
    if n_NA_row>0:
        print('Number of rows removed from covariate file due to missing observations: '+str(np.sum(NA_rows)))
        X = X[~NA_rows]
        ids = ids[~NA_rows]
    id_dict = {}
    for i in range(0,ids.shape[0]):
        id_dict[ids[i,1]] = i
    # Match with pheno_ids
    common_ids = id_dict.viewkeys() & set(ids_to_match[:,1])
    pheno_in = np.array([x in common_ids for x in ids_to_match[:,1]])
    match_ids = ids_to_match[pheno_in,1]
    X_id_match = np.array([id_dict[x] for x in match_ids])
    X = X[X_id_match, :]
    return [X,X_names,pheno_in]

######### Command line arguments #########
if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('sibgts',type=str,help='Path to bed file with sibling genotypes')
    parser.add_argument('sibped',type=str,help='Path to pedigree file with siblings sharing a family ID and non-siblings not')
    parser.add_argument('phenofile',type=str,help='Location of the phenotype file')
    parser.add_argument('outprefix',type=str,help='Location to output association statistic hdf5 file')
    parser.add_argument('--covar',type=str,help='Location of covariate file (default None)',
                        default=None)
    parser.add_argument('--fit_covariates',action='store_true',
                        help='Fit covariates for each locus. Default is to fit for null model and project out (mean) and rescale (variance)',
                        default=False)
    parser.add_argument('--tau_init',type=float,help='Initial value for ratio between shared family environmental variance and residual variance',
                        default=1)
    parser.add_argument('--phen_index',type=int,help='If the phenotype file contains multiple phenotypes, which phenotype should be analysed (default 1, first)',
                        default=1)
    parser.add_argument('--min_maf',type=float,help='Ignore SNPs with minor allele frequency below min_maf (default 0.01)',default=0.01)
    parser.add_argument('--missing_char',type=str,help='Missing value string in phenotype file (default NA)',default='NA')
    parser.add_argument('--max_missing',type=float,help='Ignore SNPs with greater percent missing calls than max_missing (default 5)',default=5)
    parser.add_argument('--append',action='store_true',default=False,help='Append results to existing output file with given outprefix (default overwrites existing')
    parser.add_argument('--no_covariate_estimates',action='store_true',default=False,help='Suppress output of covariate effect estimates')
    parser.add_argument('--fit_VC', action='store_true', default=False,
                        help='Fit the variance components for each SNP (default is to use null model MLE)')
    parser.add_argument('--start', type=int,
                        help='Start index of SNPs to perform imputation for in genotype file (starting at zero)',
                        default=0)
    parser.add_argument('--end', type=int,
                        help='End index of SNPs to perform imputation for in genotype file (goes from 0 to (end-1)',
                        default=None)
    args=parser.parse_args()

    ####################### Read in data #########################
    #### Read phenotype ###
    pheno = Pheno(args.phenofile, missing=args.missing_char).read()
    # pheno = Pheno('phenotypes/eduyears_resid.ped', missing='NA').read()
    y = np.array(pheno.val)
    pheno_ids = np.array(pheno.iid)
    if y.ndim == 1:
        pass
    elif y.ndim == 2:
        y = y[:, args.phen_index - 1]
    else:
        raise (ValueError('Incorrect dimensions of phenotype array'))
    # Remove y NAs
    y_not_nan = np.logical_not(np.isnan(y))
    if np.sum(y_not_nan) < y.shape[0]:
        y = y[y_not_nan]
        pheno_ids = pheno_ids[y_not_nan, :]
    pheno_id_dict = {}
    for i in xrange(0, y.shape[0]):
        pheno_id_dict[pheno_ids[i, 1]] = i
    pheno_fams = set(pheno_ids[:, 0])
    print('Number of non-missing phenotype observations: ' + str(y.shape[0]))

    ### Get covariates
    ## Get mean covariates
    if not args.covar == None:
        X, X_names, pheno_in = read_covariates(args.covar, pheno_ids, args.missing_char)
        n_X = X.shape[1]
        # Remove rows with missing values
        if np.sum(pheno_in) < y.shape[0]:
            y = y[pheno_in]
            pheno_ids = pheno_ids[pheno_in, :]
        # Normalise non-constant cols
        X_stds = np.std(X[:, 1:n_X], axis=0)
        X[:, 1:n_X] = zscore(X[:, 1:n_X], axis=0)
    else:
        X = np.ones((int(y.shape[0]), 1))
        n_X = 1
        X_names = np.array(['Intercept'])

    ### Read pedigree file ###
    ### Load pedigree
    ped = np.loadtxt(args.sibped, dtype='S20', skiprows=1)

    ### Create family dictionary
    fams = {}
    fam_ids = np.unique(ped[:, 0])
    for f in fam_ids:
        fams[f] = tuple(ped[ped[:, 0] == f, 1])
    # reverse lookup dict
    sib_fam_dict = {}
    for i in xrange(0, ped.shape[0]):
        sib_fam_dict[ped[i, 1]] = ped[i, 0]

    ### Read sibling genotype file ###
    #### Load genotypes
    gts_f = Bed(args.sibgts)
    gts_ids = gts_f.iid
    # Build dict
    id_dict = {}
    for i in xrange(0, gts_ids.shape[0]):
        id_dict[gts_ids[i, 1]] = i


    ### Identify siblings without genotyped parents
    # Remove individuals with genotyped parents
    parent_genotyped = np.array([ped[i, 2] in id_dict or ped[i, 3] in id_dict for i in range(0, ped.shape[0])])
    ped = ped[np.logical_not(parent_genotyped), :]
    ped_fams = np.unique(ped[:, 0])
    sibships = {}
    sibship_indices = []
    for f in ped_fams:
        pedf = ped[ped[:, 0] == f, :]
        parent_pairs = np.array([pedf[x, 2] + pedf[x, 3] for x in range(0, pedf.shape[0])])
        unique_parent_pairs = np.unique(parent_pairs)
        pcount = 0
        for par in unique_parent_pairs:
            pmatch = parent_pairs == par
            if np.sum(pmatch) > 1:
                sibs = pedf[pmatch, 1]
                sibs_genotyped = np.array([x in id_dict for x in sibs])
                if np.sum(sibs_genotyped) > 1:
                    sibships[f] = sibs[sibs_genotyped]
                    sibship_indices = sibship_indices + [id_dict[x] for x in sibs[sibs_genotyped]]
                pcount += 1
        if pcount > 1:
            print('More than one sibship without genotyped parents in family ' + str(
                f) + '. Implies incorrect/unsupported pedigree.')

    sibship_indices = np.sort(np.unique(np.array(sibship_indices)))

    # Read sibling genotypes
    print('Reading genotypes')
    if args.end is not None:
        gts = gts_f[:, args.start:args.end].read().val
        gts = gts[sibship_indices, :]
        pos = gts_f.pos[args.start:args.end, 2]
        sid = gts_f.sid[args.start:args.end]
    else:
        gts = gts_f[sibship_indices, :].read().val
        pos = gts_f.pos[:, 2]
        sid = gts_f.sid

    gts = ma.array(gts, mask=np.isnan(gts), dtype=int)

    # rebuild ID dictionary
    gts_ids = gts_ids[sibship_indices, :]
    # Build dict
    id_dict = {}
    for i in xrange(0, gts_ids.shape[0]):
        id_dict[gts_ids[i, 1]] = i

    ### Construct genetic covariate matrix
    print('Forming family-wise genotype matrix')
    gsize = 2
    G = ma.array(np.zeros((gts.shape[0], gsize, gts.shape[1]), dtype=np.float32),
                 mask=np.zeros((gts.shape[0], gsize, gts.shape[1]), dtype=bool))
    y_new = np.zeros((sibship_indices.shape[0]))
    y_new[:] = np.nan
    X_new = np.zeros((sibship_indices.shape[0], X.shape[1]))
    X_new[:] = np.nan
    fam_labels = np.zeros((sibship_indices.shape[0]), dtype='S20')
    freqs = ma.mean(gts, axis=0) / 2.0
    missingness = ma.mean(gts.mask, axis=0)
    G[:,0,:] = gts
    for i in xrange(0, sibship_indices.shape[0]):
        fam_i = sib_fam_dict[gts_ids[i, 1]]
        fam_labels[i] = fam_i
        # Find siblings
        sibs_i = sibships[fam_i]
        sibs_i = np.array([id_dict[x] for x in sibs_i])
        # Get family mean
        G[i, 1, :] = np.mean(gts[sibs_i, :], axis=0)
        # Get phenotype
        if gts_ids[i, 1] in pheno_id_dict:
            pindex = pheno_id_dict[gts_ids[i, 1]]
            y_new[i] = y[pindex]
            X_new[i, :] = X[pindex, :]

    # Set deviation from family mean
    G[:,0,:] = G[:,0,:] - G[:,1,:]

    del gts
    y = y_new
    X = X_new

    y_not_nan = np.logical_not(np.isnan(y))
    y = y[y_not_nan]
    X = X[y_not_nan, :]
    G = G[y_not_nan, :]
    fam_labels = fam_labels[y_not_nan]

    print(str(y.shape[0]) + ' genotyped individuals with phenotype data and at least one genotyped sibling')

    ######### Initialise output files ######
######### Fit Null Model ##########
    ## Get initial guesses for null model
    print('Fitting Null Model')
    # Optimize null model
    sigma_2_init = np.var(y)*args.tau_init/(1+args.tau_init)
    null_model = sibreg.model(y, X, fam_labels)
    null_optim = null_model.optimize_model(np.array([sigma_2_init,args.tau_init]))
    print('Within family variance estimate: '+str(round(null_optim['sigma2']/null_optim['tau'],4)))
    print('Residual variance estimate: ' + str(round(null_optim['sigma2'],4)))
    null_alpha = null_model.alpha_mle(null_optim['tau'],null_optim['sigma2'],compute_cov = True)
    ## Record fitting of null model
    if not args.append and not args.no_covariate_estimates and args.covar is not None:
        # Get print out for fixed mean effects
        alpha_out = np.zeros((n_X, 2))
        alpha_out[:, 0] = null_alpha[0]
        alpha_out[:, 1] = np.sqrt(np.diag(null_alpha[1]))
        # Rescale
        if n_X > 1:
            for i in xrange(0, 2):
                alpha_out[1:n_X, i] = alpha_out[1:n_X, i] / X_stds
        np.savetxt(args.outprefix + '.null_covariate_effects.txt',
                   np.hstack((X_names.reshape((n_X, 1)), np.array(alpha_out, dtype='S20'))),
                   delimiter='\t', fmt='%s')

    # Fit SNP specific models
    ### Project out mean covariates
    if not args.fit_covariates:
        # Residual y
        y=y-X.dot(null_alpha[0])
        # Reformulate fixed_effects
        X=np.ones((X.shape[0],1))
        n_X=1

    ## Output file
    outfile = h5py.File(args.outprefix+'.hdf5','w')
    outfile['sid'] = sid
    X_length = n_X + 2
    outfile.create_dataset('xtx',(G.shape[2],X_length,X_length),dtype = 'f',chunks = True, compression = 'gzip', compression_opts=9)
    outfile.create_dataset('xty', (G.shape[2], X_length), dtype='f', chunks=True, compression='gzip',
                           compression_opts=9)

    ############### Loop through loci and fit models ######################
    print('Fitting models for genome-wide SNPs')
    # Optimize model for SNP
    N_L = np.zeros((G.shape[2]), dtype=int)
    for loc in xrange(0,G.shape[2]):
        if freqs[loc] > args.min_maf and freqs[loc] < (1-args.min_maf) and (100*missingness[loc]) < args.max_missing:
            # Find NAs
            not_nans = np.sum(G[:, :, loc].mask, axis=1) == 0
            n_l = np.sum(not_nans)
            N_L[loc] = n_l
            X_l = np.ones((n_l, X_length), dtype=np.float64)
            X_l[:, 0:n_X] = X[not_nans, :]
            X_l[:, n_X:X_length] = G[not_nans, :, loc]
            model_l = sibreg.model(y[not_nans], X_l, fam_labels[not_nans])
            if args.fit_VC:
                optim_l = model_l.optimize_model(np.array([null_optim['sigma2'], null_optim['tau']]))
                if optim_l['success']:
                    alpha_l = model_l.alpha_mle(optim_l['tau'], optim_l['sigma2'], compute_cov=True, xtx_out= True)
                else:
                    raise(ValueError('Maximisation of likelihood failed for for ' + sid[loc]))
            else:
                alpha_l = model_l.alpha_mle(null_optim['tau'], null_optim['sigma2'], compute_cov=True, xtx_out= True)
            outfile['xtx'][loc,:,:] = alpha_l[0]
            outfile['xty'][loc,:] = alpha_l[1]
        else:
            outfile['xtx'][loc, :, :] = np.nan
            outfile['xty'][loc, :] = np.nan
    outfile['sigma2'] = null_optim['sigma2']
    outfile['tau'] = null_optim['tau']
    outfile['N_L'] = N_L
    outfile['freqs'] = freqs
    outfile.close()