import numpy as np
from helperfuncs import extract_upper_triangle, return_to_symmetric, extract_bounds
from scipy.optimize import fmin_l_bfgs_b
from scipy.special import comb

class sibreg_71():
    
    def __init__(self, S, theta = None):

        for s in S:
            n, m = s.shape
            assert n == m

        if theta is None:
            print("Warning there is no value for theta. Maybe consider simulating it")
        self.theta = theta
        self.S = S
        

    def simdata(self, V, N):
        
        # Simulated data (theta hats) as per section 7.1
        # V = varcov matrix of true effects
        # N = Number of obs/SNPs to generate
        
        S = self.S
        theta = self.theta

        thetahat_vec = []
        
        # make sure they are np arrays
        for i in range(N):
            
            Si = S[i]
            
            V = np.array(V)
            Si = np.array(Si)

            # get shape of V
            d = V.shape[0]
            zeromat = np.zeros(d)

            # generate true effect vector
            theta = np.random.multivariate_normal(zeromat, V)

            sim = np.random.multivariate_normal(theta, Si)
            
            # Append to vector of effects
            thetahat_vec.append(sim)
        
        thetahat_vec = np.array(thetahat_vec)
        
        self.theta = thetahat_vec

    def neg_logll_grad(self, V, theta = None, S = None):
        
        # ============================================ #
        # returns negative log likelihood and negative
        # of the gradient
        # ============================================ #
        
        theta = self.theta if theta is None else theta
        S = self.S if S is None else S

        # Unflatten V into a matrix
        d = S[0].shape[0]
        V = return_to_symmetric(V, d)
        Gvec = np.zeros((d, d))
        
        N = len(S)
        log_ll = 0
        
        for i in range(N):
            
        
            Si = S[i]
            thetai = theta[i, :]
            d, ddash = Si.shape
            assert d == ddash # Each S has to be a square matrix
      
            # calculate log likelihood
            log_ll += -(d/2) * np.log(2 * np.pi)
            log_ll += -(1/2) * np.log(np.linalg.det(Si + V))
            log_ll += -(1/2) * np.trace(np.outer(thetai, thetai) @ np.linalg.inv(Si + V))
            
            
            # calculate gradient
            SV_inv = np.linalg.inv(Si + V)
            G = -(1 / 2) * SV_inv
            G += (1 / 2) * np.dot(SV_inv,np.dot(np.outer(thetai, thetai),SV_inv))
            
            Gvec += G

        Gvec = extract_upper_triangle(Gvec)
        
        return -log_ll, -Gvec


    def solve(self,
              theta = None, 
              S = None, 
              neg_logll_grad = None,
              est_init = None,
              printout = True):
        
        # inherit parameters from the class if they aren't defined
        theta = self.theta if (theta is None) else theta
        S = self.S if (S is None) else S
        neg_logll_grad = self.neg_logll_grad if (neg_logll_grad is None) else neg_logll_grad

        # == Solves our MLE problem == #
        n, m = theta.shape
        
        if est_init is not None:
            # Shape of initial varcov guess
            rowstrue = est_init.shape[0] == m
            colstrue = est_init.shape[1] == m

            if rowstrue & colstrue:
                pass
            else:
                if printout == True:
                    print("Warning: Initial Estimate given is not of the proper dimension")
                    print("Making a matrix of 0s as the initial estimate")
                    print("=================================================")
                    
                est_init = np.zeros((m, m))
        else:
            if printout == True:
                print("No initial guess provided.")
                print("Making a matrix of 0s as the initial estimate")
                print("=================================================")
            
            est_init = np.zeros((m, m))
            
        
        # extract array from est init
        est_init_array = extract_upper_triangle(est_init) 
        
        bounds = extract_bounds(m)

        result = fmin_l_bfgs_b(
            neg_logll_grad, 
            est_init_array,
            fprime = None,
            args = (theta, S),
            bounds = bounds
        )
        
        output_matrix = return_to_symmetric(result[0], m)
        
        if printout == True:
            print("Final Estimate:\n", output_matrix)
            print("Convergence Flag: ", result[2]['task'])
            print("Number of Iterations: ", result[2]['nit'])
            print("Final Gradient: ", result[2]['grad'])
            print("Max deviation of gradient from 0: ", np.max(np.abs(result[2]['grad'] - np.zeros(3))))
        
        return output_matrix, result 

    def jackknife_se(self,
                  theta  = None, S = None,
                  blocksize = 1):

        # Simple jackknife estimator for SE
        # Source: https://www.stat.berkeley.edu/~hhuang/STAT152/Jackknife-Bootstrap.pdf
        # Default value of blocksize = 1 is the normal jackknife

        theta = self.theta if (theta is None) else theta
        S = self.S if (S is None) else S

        assert theta.shape[0] == S.shape[0]

        nobs = theta.shape[0]
        
        estimates_jk = []
        
        start_idx = 0
        while True:
            
            end_idx = start_idx + blocksize
            end_idx_cond = end_idx <= theta.shape[0]
            
            # remove ith observation
            if end_idx_cond:
                theta_jk = np.delete(theta, range(start_idx, end_idx), 
                                     axis = 0)
                S_jk = np.delete(S, range(start_idx, end_idx), 
                                 axis = 0)
            else:
                theta_jk = np.delete(theta, range(start_idx, theta.shape[0]), 
                                     axis = 0)
                S_jk = np.delete(S, range(start_idx, S.shape[0]), 
                                 axis = 0)
            
            if start_idx < theta.shape[0]:
                # Get our estimate
                output_matrix, _ = self.solve(theta = theta_jk,
                                              S = S_jk,
                                              printout = False)

                estimates_jk.append(output_matrix)

                start_idx += 1
            if not end_idx_cond:
                break
            
        estimates_jk = np.array(estimates_jk)
        
        # calculate the SE
        estimate_jk_mean = estimates_jk.mean(axis = 0)
        estimate_jk_mean = np.array([estimate_jk_mean] * estimates_jk.shape[0])
        estimates_jk_dev = estimates_jk - estimate_jk_mean
        estimates_jk_devsq = estimates_jk_dev ** 2
        estimates_jk_devsq_sum = estimates_jk_devsq.sum(axis = 0)
        
        se_correction = (nobs - blocksize)/(blocksize *comb(nobs, blocksize))

        se = se_correction * estimates_jk_devsq_sum
        se = np.sqrt(se)
        
        return se  




