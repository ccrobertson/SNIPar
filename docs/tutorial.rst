Tutorial
********
Tutorial on performing robust GWAS using family data. Before working through the tutorial, please first install the package and run the tests.

To generate the test data, in the main SNIPar directory, run:

    ``bash tests/generate_test_population.sh``

In the test_data/ directory, the file h2_quad_0.8.ped is a simulated trait with direct, paternal, and maternal effects, where 80% of the phenotypic
variance is explained by the combined direct, paternal and maternal effects of the SNPs; and the
pairwise correlations between the direct, paternal, and maternal effects is 0.5. The phenotype file is test_data/h2_quad_0.8.ped.

The genotype data has been simulated so that there are 3000 independent families, where 1000 have two siblings but no parents genotyped,
1000 have one parent genotyped and a 50% chance of having a genotyped sibling, and the final 1000 have both parents genotyped and a 50%
chance of having a genotyped sibling.

To impute the missing parental genotypes, run the following command in the main SNIPar directory:

python impute_runner.py 1 2 test_data/sample.segments.gz test_data/sample --king test_data/sample.king --agesex test_data/sample.agesex --out_prefix test_data/sample

python fGWAS.py test_data/sample1.bed test_data/sample1.hdf5 test_data/h2_quad_0.8.ped test_data/h2_quad_0.8

To impute the missing parental genotypes, type:

    ``python impute_runner.py test_data/sample.segments.gz test_data/sample1 --king test_data/sample.king --agesex test_data/sample.agesex --output_address test_data/sample1 --threads 4``

The script constructs a pedigree from the output of KING's relatedness inference (test_data/sample.king),
and age and sex information (test_data/sample.agesex). The pedigree along with the IBD segments shared between siblings recorded in test_data/sample.segments.gz are used to impute missing parental genotypes
from the sibling and observed parental genotypes in test_data/sample1.bed. The imputed parental genotypes are in a HDF5 file test_data/sample1.hdf5. The --threads 4 argument
means the imputation will run on 4 threads. If imputing for more than 1 chromosome, the --processes n argument will use n different processes in parallel, one for
each chromosome, with the number of threads per process determined by the --threads argument.

To compute summary statistics for direct, paternal, and maternal effects for all SNPs in the .bed file, type:

    ``python fGWAS.py test_data/sample1 test_data/sample1.hdf5 test_data/h2_quad_0.8.ped test_data/h2_quad_0.8``

This takes the observed genotypes in test_data/sample1.bed and the imputed parental genotypes in test_data/sample1.hdf5 and uses
them to perform, for each SNP, a joint regression onto the proband's genotype, the father's (imputed) genotype, and the mother's
(imputed) genotype. This is done using a random effects model that models phenotypic correlations between siblings,
where sibling relations are inferred from the pedigree stored in the output of the imputation script: test_data/sample1.hdf5. The 'family variance estimate'
output is the  phenotypic variance explained by mean differences between sibships, and the residual variance is the remaining phenotypic variance.
The effects are output in test_data/h2_quad_0.8.hdf5 and are given with respect to the first allele in the .bim file.

Now we have estimated locus specific summary statistics. To estimate effects and compare to the true effects, run

    ``Rscript example/estimate_sim_effects.R test_data/h2_quad_0.8.hdf5 test_data/h2_quad_0.8.effects.txt test_data/h2_quad_0.8.estimates``

This should print estimates of the bias of the effect estimates, with output something like this:

    ``[1] "bias for direct effects: 0.0281 (0.0374 S.E.)"``
    ``[1] "bias for paternal effects: -0.0376 (0.0524 S.E.)"``
    ``[1] "bias for maternal effects: 0.0528 (0.05 S.E.)"``
    ``[1] "Chi-square test p-value: 0.4879"``

If everything has worked, the bias should not be statistically significantly different from zero (with high probability).

The Chi-Square test p-value should also not be statistically significant with high probability. (This tests that the sampling distribution
of the estimates is correct, as well as the estimates being unbiased.)

The estimates along with their sampling covariance matrices and standard errors are output in test_data/h2_quad_0.8.estimates.hdf5.

If the imputation has been performed from siblings alone, then the regression onto proband, imputed paternal, and imputed maternal becomes
co-linear. This is because the imputation is the same for paternal and maternal genotypes. In this case, the regression should be performed
onto proband and sum of imputed paternal and maternal genotypes. This can be achieved by providing the --parsum option to the script:

    ``python fGWAS.py test_data/sample1 test_data/sample1.hdf5 test_data/h2_quad_0.8.ped test_data/h2_quad_0.8_parsum --parsum``

This will output estimates of direct and average parental (average of maternal and paternal) effects, along with sampling covariance
matrices and standard errors.