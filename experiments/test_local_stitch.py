"""Numerical checks for mesh coordinate conventions and distortion control."""
import unittest
import numpy as np
from local_stitch import basis, fit_mesh, limit_distortion


class MeshTests(unittest.TestCase):
    def test_smooth_displacement_generalizes_to_unseen_positions(self):
        rng=np.random.default_rng(7)
        shape=(1200,2200)
        points=rng.uniform([300,250],[1900,950],(500,2))
        def field(p):
            return np.column_stack((18*np.sin(p[:,0]/900),12*np.cos(p[:,1]/500)))
        expected=field(points)
        contaminated=expected.copy()
        contaminated[:15]+=[160,-130]
        grid=fit_mesh(points,contaminated,shape)
        test=rng.uniform([400,300],[1800,900],(200,2))
        prediction=basis(test,shape[1],shape[0])@grid.reshape(-1,2)
        self.assertLess(np.median(np.linalg.norm(prediction-field(test),axis=1)),2)

    def test_limiter_damps_fold_and_preserves_zero_field(self):
        shape=(1000,1800)
        yy,xx=np.indices((12,20))
        grid=np.stack((-2*xx*(1799/19),np.zeros_like(yy)),axis=-1)
        limited,factor,stretch=limit_distortion(grid,shape)
        self.assertLess(factor,1)
        self.assertGreaterEqual(stretch[0],.7)
        self.assertLessEqual(stretch[1],1.4)
        self.assertTrue(np.isfinite(limited).all())
        zero=np.zeros((12,20,2))
        result,factor,stretch=limit_distortion(zero,shape)
        np.testing.assert_array_equal(result,zero)
        self.assertEqual(factor,1)

    def test_inverse_grid_coordinates_recover_affine_displacement(self):
        h,w=900,1600
        y,x=np.indices((12,20))
        nodes=np.stack((.03*x*(w-1)/19, -.04*y*(h-1)/11),axis=-1)
        points=np.array([[0,0],[w-1,h-1],[724.3,241.8]])
        sampled=basis(points,w,h)@nodes.reshape(-1,2)
        np.testing.assert_allclose(sampled,points*[.03,-.04],atol=1e-4)


if __name__=='__main__':unittest.main()
