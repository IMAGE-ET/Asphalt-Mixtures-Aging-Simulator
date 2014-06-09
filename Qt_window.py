'''
Created on 2/05/2014

@author: santiago
'''
import sys
import matplotlib.image as mpimg
import numpy as np
from PyQt4 import QtGui, QtCore
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from file_loader import FileLoader
from segmentation import Segmentation


class ApplicationWindow(QtGui.QMainWindow):
    """This Class contains the main window of the DICOM sample viewer """
    timer = QtCore.QTimer()     #Timer intended to update the image

    def __init__(self):
        
        self.collection = []
        self.segmentation = Segmentation()

        QtGui.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.file_menu = QtGui.QMenu('&File', self)
        self.file_menu.addAction('&Choose path', self.open_path,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_O)
        self.file_menu.addAction('&Exit', self.fileQuit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)
        
        self.animation_menu = QtGui.QMenu('&Animation', self)
        self.action_animation_start = self.animation_menu.addAction('&Start', self.start_animation, QtCore.Qt.Key_S)
        self.action_animation_resume = self.animation_menu.addAction('&Resume', self.resume_animation, QtCore.Qt.Key_Return)
        self.action_animation_pause = self.animation_menu.addAction('&Pause', self.pause_animation, QtCore.Qt.Key_Space)
        self.menuBar().addMenu(self.animation_menu)

        self.sample_menu = QtGui.QMenu('&Sample', self)
        self.action_sample_segment = self.sample_menu.addAction('Segment sample', self.segment_sample)
        self.action_sample_3d = self.sample_menu.addAction('Show 3D model', self.show_3d_sample)
        self.action_sample_count = self.sample_menu.addAction('Count segmented elements', self.count_element_values)
        self.menuBar().addMenu(self.sample_menu)

        self.help_menu = QtGui.QMenu('&Help', self)
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.help_menu)

        self.help_menu.addAction('&About...', self.about)

        open_button = QtGui.QPushButton('Choose work path', self)
        open_button.clicked[bool].connect(self.open_path) #Button listener

        self.main_widget = QtGui.QWidget(self)

        l = QtGui.QGridLayout(self.main_widget)
        self.dc = MyDynamicMplCanvas(self.main_widget, width=5, height=4, dpi=100)
        
        self.folder_path = QtGui.QLineEdit(self)
        self.folder_path.setReadOnly(True) #The only way to edit path should be by using the button

        l.addWidget(self.folder_path, 1, 1)
        l.addWidget(open_button, 1, 2)
        l.addWidget(self.dc, 2, 1, 2, 2)

        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)
        self.menu_buttons_state()
        
    def open_path(self):
        self.update_staus("Loading files from path...")
        chosen_path = QtGui.QFileDialog.getExistingDirectory(None, 
                                                         'Open working directory', 
                                                                     'samples/6/', 
                                                    QtGui.QFileDialog.ShowDirsOnly)
        
        path = str(chosen_path+"/") #QString to Python string
        self.collection = FileLoader().load_path(path) #Load Files
        total_loaded = str(len(self.collection))+" DICOM files loaded"
        self.folder_path.setText(path)
        self.update_staus(total_loaded)
        self.menu_buttons_state(True)


    def start_animation(self):
        self.dc.reset_index()
        QtCore.QObject.connect(self.__class__.timer, QtCore.SIGNAL("timeout()"), self.dc.update_figure)
        self.__class__.timer.start(200)                #Set the update time

    def pause_animation(self):
        self.__class__.timer.stop()

    def resume_animation(self):
        self.__class__.timer.start(200)

    def update_staus(self, message):
        self.statusBar().showMessage(message)

    def segment_sample(self):
        print "Running segmentation..."
        self.dc.reset_index()
        segmented = self.segmentation.reduction(self.collection)
        reduced = self.segmentation.segment_all_samples(segmented)
        del self.collection
        self.collection = reduced
        self.update_staus("Reduction complete")
        self.action_sample_3d.setEnabled(True)  #Enables the 3D Model viewer
        self.action_sample_count.setEnabled(True) #Enables the count method


    def show_3d_sample(self):
        print "Running 3D Modeling..."
        self.update_staus("Running 3D Modeling...")
        from ToyModel3d import ToyModel3d
        ToyModel3d(self.collection)
        self.action_sample_count.setEnabled(True) #Enables the count method
    
    def count_element_values(self):
        """Shows the total count of detected elements after the segmentation"""
        empty = np.count_nonzero(self.collection==0)
        mastic = np.count_nonzero(self.collection==1)
        aggregate = np.count_nonzero(self.collection==2)
        total = (empty+mastic+aggregate)

        QtGui.QMessageBox.information(self,
                    "Total elements counted in pixels:",
                    "Sample has= "+str(total)+" pixels: \n"
                    "Empty pixels= "+str(empty)+"\t"+str((empty*100)/total)+"%.\n" 
                    "Mastic pixels= "+str(mastic)+"\t"+str((mastic*100)/total)+"%.\n"
                    "Aggregate pixels= "+str(aggregate)+"\t"+str((aggregate*100)/total)+"%.")


    def menu_buttons_state(self, state=False):
        """Enable/Disable menu options except the Count element option
        the count method requires samples to be segmented"""
        self.action_sample_count.setEnabled(False)
        self.action_sample_3d.setEnabled(False)

        self.action_animation_pause.setEnabled(state)
        self.action_animation_resume.setEnabled(state)
        self.action_animation_start.setEnabled(state)
        self.action_sample_segment.setEnabled(state)


    def fileQuit(self):
        self.pause_animation()
        self.dc.destroy()
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

    def about(self):
        QtGui.QMessageBox.about(self, "About",
        """First attempt to inplement a Qt enviroment rendering 
MatPlotLib figures created from DICOM files

        Developed by:
        Jeison Pacateque
        Santiago Puerto""")
    
    def get_collection(self):
        return self.collection
        
    def set_collection(self, collection):
        self.collection = collection
        
class Canvas(FigureCanvas):
#Set the graphical elements to show in a Qt Window
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        self.axes.hold(False) #We want the axes cleared every time plot() is called
        initial = mpimg.imread('images/python.png')
        self.axes.imshow(initial)   #Show an initial image for the app
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

#-------------------------------------------------------------------------------

class MyDynamicMplCanvas(Canvas):
    """This Class implements the canvas update method to animate the samples """
    def __init__(self, main_widget, width=5, height=4, dpi=100):
        super(MyDynamicMplCanvas, self).__init__(main_widget, width=5, height=4, dpi=100)
        self.index = 0
        self.collection = 0

    def update_figure(self):
        #Read and plot all the images stored in the image list
        if type(self.collection) == int:
            self.collection = aw.get_collection()
        if self.index != len(self.collection) : #Conditional to restart the loop
            self.axes.imshow(self.collection[self.index], cmap='seismic', interpolation='nearest')
            status_text = "Sample: "+str(self.index)
            aw.update_staus(status_text) #Show in status bar the current index
            self.index += 1
            self.draw()
        else:
            self.index=0 #When iteration catches the len(self.collection) restart the loop

    def reset_index(self):
        self.index = 0

#------------------------------------------------------------------------

qApp = QtGui.QApplication(sys.argv)
aw = ApplicationWindow()
aw.setWindowTitle("DICOM Samples Viewer")
aw.show()
sys.exit(qApp.exec_())
#qApp.exec_()