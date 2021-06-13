#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import numpy.linalg
import scipy.special as sc
import scipy.io 

class FastNoiseTracking:

    class State:

        def __init__(self, sampling_rate : int):

            self.sampling_rate = sampling_rate
            self.frame_number = 0
            self.alpha_n = 0.8
            self.alpha_ns = 0.98
            self.alpha_p = 0.2
            self.deltak = 1
            self.deltal = 2
            self.gamma_buf_pos = 0
            self.ksi_floor = 10.0**(-15.0/10)


    def __init__(self, sampling_rate : int):

        self.state = FastNoiseTracking.State(sampling_rate)


    def get_noise_psd(self, noisy_psd : np.ndarray, previous_frame_speech_psd : np.ndarray) -> np.ndarray:

        if self.state.frame_number == 0:

            self.state.frame_length = noisy_psd.shape[0]*2-2 

            self.state.K = int(self.state.frame_length/2+1)

            self.state.gamma_buf = np.zeros((self.state.K,self.state.deltal+1),dtype=np.float32)

            self.state.psi = np.zeros((self.state.K,), dtype=np.float32)

            self.state.noise_psd = noisy_psd

            gamma_ = noisy_psd/self.state.noise_psd

            self.state.gamma_buf[:,self.state.gamma_buf_pos] = gamma_

            self.state.gamma_buf_pos += 1

            self.state.p = np.zeros((self.state.K,), dtype=np.float32)

            for i in  range(self.state.K):

                f = i/self.state.frame_length * self.state.sampling_rate

                if f < 1000:

                    self.state.psi[i] = 5

                    continue
                
                if f >= 1000 and f < 3000:

                    self.state.psi[i] = 6.5

                    continue

                if f >= 3000:

                    self.state.psi[i] = 8

            N2 = self.state.noise_psd

            self.state.frame_number += 1

            return N2

        self.state.frame_number += 1

        gamma_ = noisy_psd/self.state.noise_psd

        ksi = np.maximum(self.state.alpha_ns * previous_frame_speech_psd / self.state.noise_psd + (1 - self.state.alpha_ns) * np.maximum(gamma_ - 1, 0), self.state.ksi_floor)
#
        v = gamma_/(ksi*(ksi+1))

        N = 1/(ksi+1)**2 * np.exp(np.minimum(sc.gamma(1.e-5)*sc.gammaincc(1e-5,v),10))*np.sqrt(noisy_psd)

        N2 = N * np.conjugate(N)

        self.state.gamma_buf[:,self.state.gamma_buf_pos] = gamma_

        self.state.gamma_buf_pos += 1

        if self.state.gamma_buf_pos > 2:
            
            self.state.gamma_buf_pos = 0

        gamma_avg = np.mean(self.state.gamma_buf[:,:np.amin([self.state.frame_number,3])], axis = 1)

        gamma_avg_frequency = np.zeros_like(gamma_avg)

        for i in range(self.state.K):

            gamma_avg_frequency[i] = np.mean(gamma_avg[np.amax([i-self.state.deltak,0]):np.amin([i+self.state.deltak+1,self.state.K])])

        I = np.uint32(gamma_avg_frequency > self.state.psi)

        self.state.p = self.state.alpha_p * self.state.p + (1-self.state.alpha_p)*I

        alpha_N = self.state.alpha_n+(1-self.state.alpha_n)*self.state.p

        self.state.noise_psd = alpha_N * self.state.noise_psd + (1 -alpha_N) * N2

        return self.state.noise_psd 


if __name__ == "__main__":

    noise_tracking = FastNoiseTracking(8000) # load synthetic test data

    mat = scipy.io.loadmat('./test-data/stencil.mat')

    result = np.zeros_like(mat['noisy_psd'])

    for i in range(10):

        result[:,i] = noise_tracking.get_noise_psd(mat['noisy_psd'][:,i], mat['prev_clean_speech_estimates'][:,i])


    if numpy.linalg.norm(mat['stencil']-result,ord='fro') < 1.e-7:
        print("Test passed ...")
    else:
        print("Test failed ...")






                









