#!/usr/bin/env python3
import numpy as np
import basicGcodeCmds as bgc
from modules import circles, textures, characters, perspective

from plistLoader import PlistLoader, plistPath

MANG = {}
LDLF = PlistLoader(plistPath())
LDLF.load_to_globals(MANG, ('MACH', 'GRBL', 'MAIN'))


def rotate(npx, npy, a):
    """#utility ƒ"""
    nx = npx*np.cos(a)-npy*np.sin(a)
    ny = npy*np.cos(a)+npx*np.sin(a)
    return nx, ny


class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d


cfg = ObjectView(MANG)


class Mover(object):
    def __init__(self, pitch, parent=None):
        self.pitch = pitch
        self.parent = parent
        self.path = np.array([cfg.X_PAGE/2, cfg.Y_PAGE/2])  #start at center
        self.page = np.array([cfg.X_PAGE, cfg.Y_PAGE])
        self.moments = []
        self.moves = 0
        self.rad_deviation_width = 0.5
        self.pitch_min = 0.4
        pass

    def move(self):
        if self.moves == 0:
            a = np.random.random_sample(2)*self.page
            b = self.path[-1]
        else:
            a = self.path[-2]
            b = self.path[-1]

        d = b - a
        c = np.linalg.norm(d)
        unit = (d / c)
        radius = self.pitch
        radius *= self.pitch_min + (np.random.random_sample() * (1 - self.pitch_min))

        nx = unit * radius

        aste = self.rad_deviation_width * np.random.random_sample() - self.rad_deviation_width/2
        nx = np.array(rotate(nx[0], nx[1], aste))

        check_pt = nx + b

        """
        if( /* hit vertical wall */ )
        {
            object.velocity.x *= -1;
        }
        if( /* hit horizontal wall */ )
        {
            object.velocity.y *= -1;
        }
        """
        if check_pt[0] < 0 or check_pt[0] > cfg.X_PAGE or check_pt[1] < 0 or check_pt[1] > cfg.Y_PAGE:
            nx = nx*-1.0
        # if check_pt[0] < 0 or check_pt[0] > cfg.X_PAGE:
        #     nx[1] *= -1
        #
        # if check_pt[1] < 0 or check_pt[1] > cfg.Y_PAGE:
        #     nx[0] *= -1

        self.path = np.vstack((self.path, nx + b))
        self.moves += 1

        return self.path

    def iterate(self):

        new_position = self.move()
        #draw the circle, poly, text marker, center etc


        #//return an iterable here...(points group)
        return True


def test():

    CM = Mover(200.0)
    for c in range(0, 2440):
        CM.move()

    return CM.path



if __name__ == '__main__':
    pass
