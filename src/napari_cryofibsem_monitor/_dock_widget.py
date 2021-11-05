"""
This module is an example of a barebones QWidget plugin for napari

It implements the ``napari_experimental_provide_dock_widget`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFileDialog
from magicgui import magic_factory

import glob
import os
import tifffile
import numpy as np


class ExampleQWidget(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        btn_autotem_directory = QPushButton("Select AutoTEM directort")
        btn_autotem_directory.clicked.connect(self._on_click)

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(btn_autotem_directory)

    def _on_click(self):
        directory = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        site_directories = glob.glob(os.path.join(directory,"Sites/*/"))
        im_data = []
        for site_directory in site_directories:
            
            name = os.path.split(site_directory)[-1]
            dci_images = sorted(glob.glob(os.path.join(site_directory,"DCImages/*/*.tif")))
            if len(dci_images) < 1:
                continue
            im_data.append([])
            for image_fn in dci_images:
                im = tifffile.imread(image_fn)
                if im.dtype == 'uint8':
                    im_data[-1].append(im)
        (y , x) = im_data[-1][-1].shape
        num_sites = len(im_data)
        num_img = max([len(a) for a in im_data])

        im = np.zeros((num_sites,num_img,y,x))
        for i,site in enumerate(im_data):
            for j,mage in enumerate(site):
                im[i,j,:,:] = mage
        
        self.viewer.add_image(im,name="lamellas")


@magic_factory
def example_magic_widget(img_layer: "napari.layers.Image"):
    print(f"you have selected {img_layer}")


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return [ExampleQWidget, example_magic_widget]
