#Tests for individual Optic classes
from __future__ import (absolute_import, division, print_function, unicode_literals)

import matplotlib.pyplot as pl
import numpy as np
import astropy.io.fits as fits

from .. import poppy_core
from .. import optics
from .. import zernike
from .test_core import check_wavefront



wavelength=1e-6



#def test_OpticalElement():
#    pass


#def test_FITSOpticalElement():
#    pass

#def test_Rotation():
#    pass

def test_InverseTransmission():
    """ Verify this inverts the optic throughput appropriately"""
    wave = poppy_core.Wavefront(npix=100, wavelength=wavelength)

    # vary uniform scalar transmission
    for transmission in np.arange(10, dtype=float)/10:

        optic = optics.ScalarTransmission(transmission=transmission)
        inverted = optics.InverseTransmission(optic)
        assert( np.all(  np.abs(optic.getPhasor(wave) - (1-inverted.getPhasor(wave))) < 1e-10 ))

    # vary 2d shape
    for radius in np.arange(10, dtype=float)/10:

        optic = optics.CircularAperture(radius=radius)
        inverted = optics.InverseTransmission(optic)
        assert( np.all(  np.abs(optic.getPhasor(wave) - (1-inverted.getPhasor(wave))) < 1e-10 ))

        assert optic.shape==inverted.shape


#------ Generic Analytic elements -----

def test_scalar_transmission():
    """ Verify this adjusts the wavefront intensity appropriately """
    wave = poppy_core.Wavefront(npix=100, wavelength=wavelength)

    for transmission in [1.0, 1.0e-3, 0.0]:

        optic = optics.ScalarTransmission(transmission=transmission)
        assert( np.all(optic.getPhasor(wave) == transmission))



def test_roundtrip_through_FITS():
    """ Verify we can make an analytic element, turn it into a FITS file and back,
    and get the same thing
    """
    optic = optics.ParityTestAperture()
    array = optic.sample(npix=512)

    fitsfile = optic.to_fits(npix=512)
    optic2 = poppy_core.FITSOpticalElement(transmission=fitsfile)

    assert np.all(optic2.amplitude == array), "Arrays before/after casting to FITS file didn't match"


#------ Analytic Image Plane elements -----

def test_RectangularFieldStop():
    optic= optics.RectangularFieldStop(width=1, height=10)
    wave = poppy_core.Wavefront(npix=100, pixelscale=0.1, wavelength=1e-6) # 10x10 arcsec square

    wave*= optic
    assert wave.shape[0] == 100
    assert wave.intensity.sum() == 1000 # 1/10 of the 1e4 element array


def test_SquareFieldStop():
    optic= optics.SquareFieldStop(size=2)
    wave = poppy_core.Wavefront(npix=100, pixelscale=0.1, wavelength=1e-6) # 10x10 arcsec square

    wave*= optic
    assert wave.shape[0] == 100
    assert wave.intensity.sum() == 400 # 1/10 of the 1e4 element array



def test_BarOcculter():
    optic= optics.BarOcculter(width=1, angle=0)
    wave = poppy_core.Wavefront(npix=100, pixelscale=0.1, wavelength=1e-6) # 10x10 arcsec square

    wave*= optic
    assert wave.shape[0] == 100
    assert wave.intensity.sum() == 9000 # 9/10 of the 1e4 element array


def test_AnnularFieldStop():
    optic= optics.AnnularFieldStop(radius_inner=1.0, radius_outer=2.0)
    wave = poppy_core.Wavefront(npix=100, pixelscale=0.1, wavelength=1e-6) # 10x10 arcsec square

    wave*= optic
    # Just check a handful of points that it goes from 0 to 1 back to 0
    np.testing.assert_almost_equal( wave.intensity[50,50], 0)
    np.testing.assert_almost_equal( wave.intensity[55,50], 0)
    np.testing.assert_almost_equal( wave.intensity[60,50], 1)
    np.testing.assert_almost_equal( wave.intensity[68,50], 1)
    np.testing.assert_almost_equal( wave.intensity[75,50], 0)
    np.testing.assert_almost_equal( wave.intensity[95,50], 0)
    # and check the area is approximately right
    expected_area = np.pi*(optic.radius_outer**2 - optic.radius_inner**2) * 100

    # updated criteria for dealing with gray pixels
    # sum of pixels should be close to this, and just a bit less than it
    area = wave.intensity.sum()
    assert expected_area-area < 0.05*expected_area
    assert expected_area-area >0
    # if we count the number of pixels that are significantly nonzero
    # it should be a bit above the desired area
    area_upper_bound = (wave.intensity > 0.01).sum()
    assert area_upper_bound > expected_area
    assert area_upper_bound < expected_area*1.1


def test_BandLimitedOcculter(halfsize = 5) :
    # For now, just tests the center pixel value.
    # See https://github.com/mperrin/poppy/issues/137

    mask = optics.BandLimitedCoron( kind = 'circular',  sigma = 1.)

    # odd number of pixels; center pixel should be 0
    sample = mask.sample(npix = 2*halfsize+1, grid_size = 10, what = 'amplitude')
    assert sample[halfsize, halfsize] == 0
    assert sample[halfsize, halfsize] != sample[halfsize-1, halfsize]
    assert sample[halfsize+1, halfsize] == sample[halfsize-1, halfsize]

    # even number of pixels; center 4 should be equal
    sample2 = mask.sample(npix = 2*halfsize, grid_size = 10, what = 'amplitude')
    assert sample2[halfsize, halfsize] != 0
    assert sample2[halfsize-1, halfsize-1] == sample2[halfsize, halfsize]
    assert sample2[halfsize-1, halfsize] == sample2[halfsize, halfsize]
    assert sample2[halfsize, halfsize-1] == sample2[halfsize, halfsize]



def test_rotations():
    # Some simple tests of the rotation code on AnalyticOpticalElements. Incomplete!

    # rotating a square by +45 and -45 should give the same result
    ar1 = optics.SquareAperture(rotation=45, size=np.sqrt(2)).sample(npix=256, grid_size=2)
    ar2 = optics.SquareAperture(rotation=-45, size=np.sqrt(2)).sample(npix=256, grid_size=2)
    assert np.allclose(ar1,ar2)

    # rotating a rectangle with flipped side lengths by 90 degrees should give the same result
    fs1 = optics.RectangularFieldStop(width=1, height=10).sample(npix=256, grid_size=10)
    fs2 = optics.RectangularFieldStop(width=10, height=1, rotation=90).sample(npix=256, grid_size=10)
    assert np.allclose(fs1,fs2)

    # check some pixel values for a 45-deg rotated rectangle
    fs3 = optics.RectangularFieldStop(width=10, height=1, rotation=45).sample(npix=200, grid_size=10)
    for i in [50, 100, 150]:
        assert fs3[i, i]==1
        assert fs3[i, i+20]!=1
        assert fs3[i, i-20]!=1

#def test_rotations_RectangularFieldStop():
#
#    # First let's do a rotation of the wavefront itself by 90^0 after an optic
#
#    # now try a 90^0 rotation for the field stop at that optic. Assuming perfect system w/ no aberrations when comparing rsults. ?
#    fs = poppy_core.RectangularFieldStop(width=1, height=10, ang;le=90)
#    wave = poppy_core.Wavefront(npix=100, pixelscale=0.1, wavelength=1e-6) # 10x10 arcsec square
#
#    wave*= fs
#    assert wave.shape[0] == 100
#    assert fs.intensity.sum() == 1000 # 1/10 of the 1e4 element array
#
#


#------ Analytic Pupil Plane elements -----

def test_ParityTestAperture():
    """ Verify that this aperture is not symmetric in either direction"""
    wave = poppy_core.Wavefront(npix=100, wavelength=wavelength)

    array = optics.ParityTestAperture().getPhasor(wave)

    assert np.any(array[::-1,:] != array)
    assert np.any(array[:,::-1] != array)


def test_RectangleAperture():
    """ Test rectangular aperture
    based on areas of 2 different rectangles,
    and also that the rotation works to swap the axes
    """
    optic= optics.RectangleAperture(width=5, height=3)
    wave = poppy_core.Wavefront(npix=100, diam=10.0, wavelength=1e-6) # 10x10 meter square
    wave*= optic
    assert wave.shape[0] == 100
    assert wave.intensity.sum() == 1500 # 50*30 pixels of the 1e4 element array

    optic= optics.RectangleAperture(width=2, height=7)
    wave = poppy_core.Wavefront(npix=100, diam=10.0, wavelength=1e-6) # 10x10 arcsec square
    wave*= optic
    assert wave.shape[0] == 100
    assert wave.intensity.sum() == 1400 # 50*30 pixels of the 1e4 element array


    optic1= optics.RectangleAperture(width=2, height=7, rotation=90)
    optic2= optics.RectangleAperture(width=7, height=2)
    wave1 = poppy_core.Wavefront(npix=100, diam=10.0, wavelength=1e-6) # 10x10 arcsec square
    wave2= poppy_core.Wavefront(npix=100, diam=10.0, wavelength=1e-6) # 10x10 arcsec square
    wave1*= optic1
    wave2*= optic2

    assert wave1.shape[0] == 100
    assert np.all(np.abs(wave1.intensity - wave2.intensity) < 1e-6)




def test_HexagonAperture(display=False):
    """ Tests creating hexagonal aperture """

    # should make hexagon PSF and compare to analytic expression
    optic= optics.HexagonAperture(side=1)
    wave = poppy_core.Wavefront(npix=100, diam=10.0, wavelength=1e-6) # 10x10 meter square
    wave*= optic
    if display: optic.display()

def test_MultiHexagonAperture(display=False):
    # should make multihexagon PSF and compare to analytic expression
    optic= optics.MultiHexagonAperture(side=1, rings=2)
    wave = poppy_core.Wavefront(npix=100, diam=10.0, wavelength=1e-6) # 10x10 meter square
    wave*= optic
    if display: optic.display()


def test_NgonAperture(display=False):
    """ Test n-gon aperture

    Note we could better test this if we impemented symmetry checks using the rotation argument?
    """
    # should make n-gon PSF for n=4, 6 and compare to square and hex apertures
    optic= optics.NgonAperture(nsides=4, radius=1, rotation=45)
    wave = poppy_core.Wavefront(npix=100, diam=10.0, wavelength=1e-6) # 10x10 meter square
    wave*= optic
    if display:
        pl.subplot(131)
        optic.display()

    optic= optics.NgonAperture(nsides=5, radius=1)
    wave = poppy_core.Wavefront(npix=100, diam=10.0, wavelength=1e-6) # 10x10 meter square
    wave*= optic
    if display:
        pl.subplot(132)
        optic.display()



    optic= optics.NgonAperture(nsides=6, radius=1)
    wave = poppy_core.Wavefront(npix=100, diam=10.0, wavelength=1e-6) # 10x10 meter square
    wave*= optic
    if display:
        pl.subplot(133)
        optic.display()



def test_ObscuredCircularAperture_Airy(display=False):
    """ Compare analytic 2d Airy function with the results of a POPPY
    numerical calculation of the PSF for a circular aperture.

    Note that we expect very close but not precisely perfect agreement due to
    the quantization of the POPPY PSF relative to a perfect geometric circle.
    """

    from ..misc import airy_2d

    pri_diam = 1
    sec_diam = 0.4
    # Analytic PSF for 1 meter diameter aperture
    analytic = airy_2d(diameter=pri_diam, obscuration=sec_diam/pri_diam)
    analytic /= analytic.sum() # for comparison with poppy outputs normalized to total=1


    # Numeric PSF for 1 meter diameter aperture
    osys = poppy_core.OpticalSystem()
    osys.addPupil(
            optics.CompoundAnalyticOptic( [optics.CircularAperture(radius=pri_diam/2) ,
                                           optics.SecondaryObscuration(secondary_radius=sec_diam/2, n_supports=0) ]) )
    osys.addDetector(pixelscale=0.010,fov_pixels=512, oversample=1)
    numeric = osys.calcPSF(wavelength=1.0e-6, display=False)

    # Comparison
    difference = numeric[0].data-analytic
    #assert np.all(np.abs(difference) < 3e-5)


    if display:
        from .. import utils
        #comparison of the two
        from matplotlib.colors import LogNorm
        norm = LogNorm(vmin=1e-6, vmax=1e-2)

        pl.figure(figsize=(15,5))
        pl.subplot(141)
        ax1=pl.imshow(analytic, norm=norm)
        pl.title("Analytic")
        pl.subplot(142)
        #ax2=pl.imshow(numeric[0].data, norm=norm)
        utils.display_PSF(numeric, vmin=1e-6, vmax=1e-2, colorbar=False)
        pl.title("Numeric")
        pl.subplot(143)
        ax2=pl.imshow(numeric[0].data-analytic, norm=norm)
        pl.title("Difference N-A")
        pl.subplot(144)
        ax2=pl.imshow(np.abs(numeric[0].data-analytic) < 1e-4)
        pl.title("Difference <1e-4")


def test_CompoundAnalyticOptic(display=False):
    wavelen = 2e-6
    nwaves = 2
    r = 3

    osys_compound = poppy_core.OpticalSystem()
    osys_compound.addPupil(
        optics.CompoundAnalyticOptic([
            optics.CircularAperture(radius=r),
            optics.ThinLens(nwaves=nwaves, reference_wavelength=wavelen,
                            radius=r)
        ])
    )
    osys_compound.addDetector(pixelscale=0.010, fov_pixels=512, oversample=1)
    psf_compound = osys_compound.calcPSF(wavelength=wavelen, display=False)

    osys_separate = poppy_core.OpticalSystem()
    osys_separate.addPupil(optics.CircularAperture(radius=r))    # pupil radius in meters
    osys_separate.addPupil(optics.ThinLens(nwaves=nwaves, reference_wavelength=wavelen,
                                           radius=r))
    osys_separate.addDetector(pixelscale=0.01, fov_pixels=512, oversample=1)
    psf_separate = osys_separate.calcPSF(wavelength=wavelen, display=False)

    if display:
        from matplotlib import pyplot as plt
        from poppy import utils
        plt.figure()
        plt.subplot(1, 2, 1)
        utils.display_PSF(psf_separate, title='From Separate Optics')
        plt.subplot(1, 2, 2)
        utils.display_PSF(psf_compound, title='From Compound Optics')

    difference = psf_compound[0].data - psf_separate[0].data

    assert np.all(np.abs(difference) < 1e-3)



def test_AsymmetricObscuredAperture(display=False):
    """  Test that we can run the code with asymmetric spiders
    """

    from ..misc import airy_2d

    pri_diam = 1
    sec_diam = 0.4
    # Analytic PSF for 1 meter diameter aperture
    analytic = airy_2d(diameter=pri_diam, obscuration=sec_diam/pri_diam)
    analytic /= analytic.sum() # for comparison with poppy outputs normalized to total=1


    # Numeric PSF for 1 meter diameter aperture
    osys = poppy_core.OpticalSystem()
    osys.addPupil(
            optics.CompoundAnalyticOptic( [optics.CircularAperture(radius=pri_diam/2) ,
                                           optics.AsymmetricSecondaryObscuration(secondary_radius=sec_diam/2, support_angle=[0,150,210], support_width=0.1) ]) )
    osys.addDetector(pixelscale=0.030,fov_pixels=512, oversample=1)
    if display: osys.display()
    numeric = osys.calcPSF(wavelength=1.0e-6, display=False)

    # Comparison
    difference = numeric[0].data-analytic
    #assert np.all(np.abs(difference) < 3e-5)


    if display:
        from .. import utils
        #from matplotlib.colors import LogNorm
        #norm = LogNorm(vmin=1e-6, vmax=1e-2)

        #ax2=pl.imshow(numeric[0].data, norm=norm)
        utils.display_PSF(numeric, vmin=1e-8, vmax=1e-2, colorbar=False)
        #pl.title("Numeric")

def test_GaussianAperture(display=False):
    """ Test the Gaussian aperture """

    ga = optics.GaussianAperture(fwhm=1)
    w = poppy_core.Wavefront(npix=101) # enforce odd npix so there is a pixel at the exact center

    w *= ga

    assert(ga.w == ga.fwhm/(2*np.sqrt(np.log(2))))

    assert(w.intensity.max() ==1)


    # now mock up a wavefront with very specific coordinate values
    # namely the origin, one HWHM away, and one w or sigma away.
    class mock_wavefront(poppy_core.Wavefront):
        def __init__(self, *args, **kwargs):
            #super(poppy.Wavefront, self).__init__(*args, **kwargs) # super does not work for some reason?
            poppy_core.Wavefront.__init__(self, *args, **kwargs)

            self.wavefront = np.ones(5)
            self.planetype=poppy_core.PlaneType.pupil
            self.pixelscale = 0.5
        def coordinates(self):
            return (np.asarray([0,0.5, 0.0, ga.w, 0.0]), np.asarray([0, 0, 0.5, 0, -ga.w ]))

    trickwave = mock_wavefront()
    trickwave *= ga
    assert(trickwave.amplitude[0]==1)
    assert(np.allclose(trickwave.amplitude[1:3], 0.5))
    assert(np.allclose(trickwave.amplitude[3:5], np.exp(-1)))


def test_ThinLens(display=False):
    pupil_radius = 1

    pupil = optics.CircularAperture(radius=pupil_radius)
    # let's add < 1 wave here so we don't have to worry about wrapping
    lens = optics.ThinLens(nwaves=0.5, reference_wavelength=1e-6, radius=pupil_radius)
    # n.b. npix is 99 so that there are an integer number of pixels per meter (hence multiple of 3)
    # and there is a central pixel at 0,0 (hence odd npix)
    # Otherwise the strict test against half a wave min max doesn't work
    # because we're missing some (tiny but nonzero) part of the aperture
    wave = poppy_core.Wavefront(npix=99, diam=3.0, wavelength=1e-6)
    wave *= pupil
    wave *= lens

    assert np.abs(wave.phase.max() - np.pi/2) < 1e-19
    assert np.abs(wave.phase.min() + np.pi/2) < 1e-19

    # regression test to ensure null optical elements don't change ThinLens behavior
    # see https://github.com/mperrin/poppy/issues/14
    osys = poppy_core.OpticalSystem()
    osys.addPupil(optics.CircularAperture(radius=1))
    for i in range(10):
        osys.addImage()
        osys.addPupil()

    osys.addPupil(optics.ThinLens(nwaves=0.5, reference_wavelength=1e-6,
                                  radius=pupil_radius))
    osys.addDetector(pixelscale=0.01, fov_arcsec=3.0)
    psf = osys.calcPSF(wavelength=1e-6)

    osys2 = poppy_core.OpticalSystem()
    osys2.addPupil(optics.CircularAperture(radius=1))
    osys2.addPupil(optics.ThinLens(nwaves=0.5, reference_wavelength=1e-6,
                                   radius=pupil_radius))
    osys2.addDetector(pixelscale=0.01, fov_arcsec=3.0)
    psf2 = osys2.calcPSF()


    if display:
        import poppy
        poppy.display_PSF(psf)
        poppy.display_PSF(psf2)

    assert np.allclose(psf[0].data,psf2[0].data), (
        "ThinLens shouldn't be affected by null optical elements! Introducing extra image planes "
        "made the output PSFs differ beyond numerical tolerances."
    )
