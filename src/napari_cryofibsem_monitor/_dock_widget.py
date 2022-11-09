"""
This module is an example of a barebones QWidget plugin for napari

It implements the ``napari_experimental_provide_dock_widget`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QWidget, QVBoxLayout,  QHBoxLayout,QPushButton, QFileDialog, QGroupBox

from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import glob
import os
import tifffile
import numpy as np

import imreg_dft as ird

pixel_size_nm = 50.8

def width_plot(im):
    cutout = im[196:312,340:440]
    prof = np.average(cutout,axis=1)
    return(prof)

class ExampleQWidget(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.image_layer = None

        btn_autotem_directory = QPushButton("Select AutoTEM directort")
        btn_autotem_directory.clicked.connect(self._on_click)

        self.btn_update = QPushButton("Update")
        self.btn_update.clicked.connect(self._on_click_update)
        self.btn_update.setEnabled(False)

        loading_box = QGroupBox("Load Data")
        loading_box.setLayout(QHBoxLayout())
        loading_box.layout().addWidget(btn_autotem_directory)
        loading_box.layout().addWidget(self.btn_update)

        
        btn_align_site = QPushButton("Align Site")
        btn_align_site.clicked.connect(self._on_click_align_site)
        btn_align_all = QPushButton("Align All")
        alignment_box = QGroupBox("Alignment")
        alignment_box.setLayout(QHBoxLayout())
        alignment_box.layout().addWidget(btn_align_site)
        alignment_box.layout().addWidget(btn_align_all)

        with plt.style.context('dark_background'):
            plt.rcParams['figure.dpi'] = 110
            thickness_widget = FigureCanvas(Figure(figsize=(8.5, 13)))
            self.static_ax = thickness_widget.figure.subplots()
            self.static_ax.prof_plot = self.static_ax.plot(np.arange(116) * pixel_size_nm,np.zeros(116))
            
            self.static_ax.set_autoscale_on(True) # enable autoscale
            self.static_ax.autoscale_view(True,True,True)
            self.static_ax.set_xlabel("Y-axis [nm]")
            self.static_ax.thick_label = self.static_ax.text(0.95, 0.95, '',
            verticalalignment='top', horizontalalignment='right',
            transform=self.static_ax.transAxes,
            color='green', fontsize=15)
        thickness_box = QGroupBox("Thickness")
        thickness_box.setLayout(QVBoxLayout())
        thickness_box.layout().addWidget(thickness_widget)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(loading_box)
        self.layout().addWidget(alignment_box)
        self.layout().addWidget(thickness_box)

    def _on_click(self):
        directory = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        self.site_directories = glob.glob(os.path.join(directory,"Sites/*/"))
        self.update()
        self.btn_update.setEnabled(True)
        self.viewer.dims.axis_labels = ("Lamella","Step","Y","X")
        self.viewer.dims.events.current_step.connect(self.update_plot)
        
    def update(self):
        im_data = []
        self.names = []
        for site_directory in self.site_directories:
            dci_images = sorted(glob.glob(os.path.join(site_directory,"DCImages/*/*.tif")))
            if len(dci_images) < 1:
                continue
            self.names.append(os.path.split(site_directory)[-2])
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
                if mage.shape == (y,x):
                    im[i,j,:,:] = mage
                else:
                    im[i,j,:mage.shape[0],:mage.shape[1]] = mage
        
        if self.image_layer is None:
            self.image_layer = self.viewer.add_image(im,name="Cryo-FIB lamellas")
        else:
            self.image_layer.data = im
        

    def _on_click_update(self):
        self.update()
    
    def _on_click_align_site(self):
        images = self.image_layer.data[self.viewer.dims.current_step[0]]
        prev_im = None
        for i,im in enumerate(images): 
            if prev_im is not None:
                result = ird.translation(prev_im, im)
                tvec = result["tvec"].round(4)
                # the Transformed IMaGe.
                timg = ird.transform_img(im, tvec=tvec)
            else:
                timg = im    
            images[i,:,:] = timg
            prev_im = timg
        self.image_layer.data[self.viewer.dims.current_step[0]] = images

    def update_plot(self, event):
        prof = width_plot(self.image_layer.data[event.value[0],event.value[1],:,:])
        dat = self.static_ax.prof_plot[0].get_data()
        self.static_ax.prof_plot[0].set_data(dat[0],prof)
        if hasattr(self.static_ax, "fill_plot"):
            self.static_ax.fill_plot.remove()
        self.static_ax.fill_plot = self.static_ax.fill_between(dat[0],np.max(prof)*0.1,prof,interpolate=True,where=prof > np.max(prof*0.1),color="red")
        right_end = max([np.max(path.vertices[:,0]) for path in self.static_ax.fill_plot.get_paths()])
        left_end = min([np.min(path.vertices[:,0]) for path in self.static_ax.fill_plot.get_paths()])
        thickness = right_end-left_end
        self.static_ax.thick_label.set_text(f"{self.names[event.value[0]]}: {thickness:.1f} nm")
        self.static_ax.relim()        # Recalculate limits
        self.static_ax.autoscale_view(True,True,True)
        self.static_ax.figure.canvas.draw()

def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return [ExampleQWidget]
