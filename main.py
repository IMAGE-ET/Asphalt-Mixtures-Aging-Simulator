'''
Created on 2/05/2014

@author: santiago
'''
import sys
import matplotlib.image as mpimg
import os
from PyQt4 import QtGui, QtCore
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from file_loader import FileLoader
from segmentation import Segmentation
from simulation_engine import SimulationEngine
from results import Result


class ApplicationWindow(QtGui.QMainWindow):
    """This Class contains the main window of the program"""

    def __init__(self):
        self.timer = QtCore.QTimer()     #Timer intended to update the image
        self.collection = []
        self.segmented_collection = []
        self.segmentation = Segmentation()

        QtGui.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.file_menu = QtGui.QMenu('&File', self)
        self.file_menu.addAction('&Choose path', self.open_path, QtCore.Qt.CTRL + QtCore.Qt.Key_O)
        self.action_file_writevtk = self.file_menu.addAction('Write VTK file', self.write_vtk_file, QtCore.Qt.CTRL + QtCore.Qt.Key_W)
        self.file_menu.addAction('&Exit', self.fileQuit, QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)

        self.animation_menu = QtGui.QMenu('&Animation', self)
        self.action_animation_start = self.animation_menu.addAction('&Start', self.start_animation, QtCore.Qt.Key_S)
        self.action_animation_resume = self.animation_menu.addAction('&Resume', self.resume_animation, QtCore.Qt.Key_Return)
        self.action_animation_pause = self.animation_menu.addAction('&Pause', self.pause_animation, QtCore.Qt.Key_Space)
        self.menuBar().addMenu(self.animation_menu)

        self.sample_menu = QtGui.QMenu('&Sample', self)
        self.action_sample_segment = self.sample_menu.addAction('&Segment sample', self.segment_sample, QtCore.Qt.CTRL + QtCore.Qt.Key_S)
        self.action_sample_3d = self.sample_menu.addAction('&Show 3D model', self.show_3d_sample)
        self.action_sample_count = self.sample_menu.addAction('&Count segmented elements', self.count_element_values)
        self.menuBar().addMenu(self.sample_menu)

        self.simulation_menu = QtGui.QMenu('&Simulation', self)
        self.simulation_setup = self.simulation_menu.addAction('&Set up simulation...', self.setup_simulation)
        self.simulation_run = self.simulation_menu.addAction('&Run simulation...', self.run_simulation)
        self.menuBar().addMenu(self.simulation_menu)

        self.help_menu = QtGui.QMenu('&Help', self)
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.help_menu)

        self.help_menu.addAction('&Help', self.help_dialog)
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
        self.pause_animation();
        self.update_staus("Loading files from path...")
        current_path = os.path.dirname(os.path.abspath(__file__))+'/samples/4/'
        print current_path
        chosen_path = QtGui.QFileDialog.getExistingDirectory(None,
                                                         'Open working directory',
                                                                     current_path,
                                                   QtGui.QFileDialog.ShowDirsOnly)

        path = str(chosen_path+"/") #QString to Python string
        #Prevents the execution of load_path if the user don't select a folder
        if path != "/":
            self.collection = FileLoader().load_path(path) #Load Files
            total_loaded = str(len(self.collection))+" DICOM files loaded."
            self.folder_path.setText(path)
            self.update_staus(total_loaded)
            self.menu_buttons_state(True)
            QtGui.QMessageBox.about(self, "Information:", total_loaded)


    def start_animation(self):
        self.dc.reset_index()
        QtCore.QObject.connect(self.timer, QtCore.SIGNAL("timeout()"), self.dc.update_figure)
        self.timer.start(150)                #Set the update time

    def pause_animation(self):
        self.timer.stop()

    def resume_animation(self):
        self.timer.start(150)

    def update_staus(self, message):
        self.statusBar().showMessage(message)

    def segment_sample(self):
        print "Running segmentation..."
        self.update_staus("Running segmentation...")

        self.dc.reset_index()

        segmented = self.segmentation.reduction(self.collection)
        reduced = self.segmentation.segment_all_samples(segmented)
        del self.collection
        self.segmented_collection = reduced
        self.collection = self.segmented_collection
        self.update_staus("Reduction complete")
        self.count_element_values()

        self.action_sample_3d.setEnabled(True)  #Enables the 3D Model viewer
        self.action_sample_count.setEnabled(True) #Enables the count method
        self.action_file_writevtk.setEnabled(True) #Enables the VTK writer
        self.simulation_setup.setEnabled(True) #Enables the simulation setup
        self.simulation_run.setEnabled(True) #Enables the simulation setup

        self.action_sample_segment.setEnabled(False) #Disables de segmentation action


    def show_3d_sample(self):
        print "Running 3D Modeling..."
        self.update_staus("Running 3D Modeling...")
        from render_3d import ToyModel3d
        ToyModel3d(self.collection)
        self.action_sample_count.setEnabled(True) #Enables the count method

    def write_vtk_file(self):
        print "Writting VTK file from loaded model..."
        from fem import VectorWriter
        filename = QtGui.QFileDialog.getSaveFileName(self, 'Save File', 'ToyModel.vtk')
        vectorizer = VectorWriter()
        vectorizer.save_vtk(self.collection, filename)
        QtGui.QMessageBox.about(self, "Alert","File saved at "+filename)

    def count_element_values(self):
        import numpy as np
        """Shows the total count of detected elements after the segmentation"""
        empty = np.count_nonzero(self.collection==0)
        mastic = np.count_nonzero(self.collection==1)
        aggregate = np.count_nonzero(self.collection==2)
        total = (empty+mastic+aggregate)

        QtGui.QMessageBox.information(self,
                    "Segmentation and reduction done",
                    "Sample has= "+str(total)+" pixels: \n"
                    "Empty pixels= "+str(empty)+"\t"+str((empty*100.)/total)+"%.\n"
                    "Mastic pixels= "+str(mastic)+"\t"+str((mastic*100.)/total)+"%.\n"
                    "Aggregate pixels= "+str(aggregate)+"\t"+str((aggregate*100.)/total)+"%.")


    def menu_buttons_state(self, state=False):
        """Enable/Disable menu options except the Count element option
        the count method requires samples to be segmented"""
        self.action_sample_count.setEnabled(False)
        self.action_sample_3d.setEnabled(False)
        self.action_file_writevtk.setEnabled(False)
        self.simulation_setup.setEnabled(False)
        self.simulation_run.setEnabled(False)

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
        """Asphalt Mixtures Aging Simulator

        Developed by:
        Jeison Pacateque
        Santiago Puerto

        Universidad Distrital Francisco Jose de Caldas
        """)

    def help_dialog(self):
        QtGui.QMessageBox.about(self, "Help",
        """Asphalt Mixtures Aging Simulator

        The help should be here:

        Universidad Distrital Francisco Jose de Caldas
        """)

    def get_collection(self):
        return self.collection

    def set_collection(self, collection):
        self.collection = collection

    def setup_simulation(self):
        config_dialog = ConfigureSimulationDialog()
        config_dialog.exec_() #Prevents the dialog to disappear

    def run_simulation(self):
        print "Run simulation"
        engine = SimulationEngine()


class Canvas(FigureCanvas):
    """Set the graphical elements to show in a Qt Window"""
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
        self.collection = "Empty"

    def update_figure(self):
        """Read and plot all the images stored in the image list"""
        if type(self.collection) == str:
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
        self.collection = "Empty"

#------------------------------------------------------------------------
class ConfigureSimulationDialog(QtGui.QDialog):

    def __init__(self):
        super(ConfigureSimulationDialog, self).__init__()

        self.title = QtGui.QLabel('Configure the physical constants')

        self.mechanicsLabel = QtGui.QLabel("Young's modulus")
        self.modulusAggregateLabel = QtGui.QLabel("Aggregate:")
        self.modulusMasticLabel = QtGui.QLabel("Mastic:")
        self.modulusAirLabel = QtGui.QLabel("Air voids:")

        self.aggregate_YM = QtGui.QLineEdit()
        self.mastic_YM = QtGui.QLineEdit()
        self.air_YM = QtGui.QLineEdit()

        self.thermalLabel = QtGui.QLabel("Thermal conductivity")
        self.thermalAggregateLabel = QtGui.QLabel("Aggregate:")
        self.thermalMasticLabel = QtGui.QLabel("Mastic:")
        self.thermalAirLabel = QtGui.QLabel("Air voids:")

        self.aggregate_TC = QtGui.QLineEdit()
        self.mastic_TC = QtGui.QLineEdit()
        self.air_TC = QtGui.QLineEdit()

        self.chemicalLabel = QtGui.QLabel("Chemical constants")
        self.chemicalAggregateLabel = QtGui.QLabel("Chemical value1:")
        self.chemicalMasticLabel = QtGui.QLabel("Chemical value2:")
        self.chemicalAirLabel = QtGui.QLabel("Chemical value3:")

        self.aggregate_CH = QtGui.QLineEdit()
        self.mastic_CH = QtGui.QLineEdit()
        self.air_CH = QtGui.QLineEdit()

        self.runSimulationButton = QtGui.QPushButton('Run simulation', self)
        self.runSimulationButton.clicked[bool].connect(self.runSimulation) #Listener

        self.cancelButton =  QtGui.QPushButton('Cancel', self)
        self.cancelButton.clicked[bool].connect(self.closeWindow)

        self.grid = QtGui.QGridLayout()
        self.grid.setSpacing(1)

        self.grid.addWidget(self.title, 1, 0)

        self.grid.addWidget(self.mechanicsLabel, 2, 0)
        self.grid.addWidget(self.modulusAggregateLabel, 3, 0)
        self.grid.addWidget(self.aggregate_YM, 3, 1)
        self.grid.addWidget(self.modulusMasticLabel, 4, 0)
        self.grid.addWidget(self.mastic_YM, 4, 1)
        self.grid.addWidget(self.modulusAirLabel, 5, 0)
        self.grid.addWidget(self.air_YM, 5, 1)

        self.grid.addWidget(self.thermalLabel, 6, 0)
        self.grid.addWidget(self.thermalAggregateLabel, 7, 0)
        self.grid.addWidget(self.aggregate_TC, 7, 1)
        self.grid.addWidget(self.thermalMasticLabel, 8, 0)
        self.grid.addWidget(self.mastic_TC, 8, 1)
        self.grid.addWidget(self.thermalAirLabel, 9, 0)
        self.grid.addWidget(self.air_TC, 9, 1)

        self.grid.addWidget(self.chemicalLabel, 10, 0)
        self.grid.addWidget(self.chemicalAggregateLabel, 11, 0)
        self.grid.addWidget(self.aggregate_CH, 11, 1)
        self.grid.addWidget(self.chemicalMasticLabel, 12, 0)
        self.grid.addWidget(self.mastic_CH, 12, 1)
        self.grid.addWidget(self.chemicalAirLabel, 13, 0)
        self.grid.addWidget(self.air_CH, 13, 1)

        self.grid.addWidget(self.runSimulationButton, 14, 1)
        self.grid.addWidget(self.cancelButton, 14, 2)


        self.setLayout(self.grid)

        self.setGeometry(300, 300, 350, 300)
        self.setWindowTitle('Configure Simulation')
        self.setDefaultValues()
        self.show()


    def setDefaultValues(self, E2=21000000, E1=10000000, E0=100, conductAsphalt=0.75,
                         conductRock=7.8, conductAir=0.026):
        self.aggregate_YM.setText(str(E2))
        self.mastic_YM.setText(str(E1))
        self.air_YM.setText(str(E0))
        self.aggregate_TC.setText(str(conductRock))
        self.mastic_TC.setText(str(conductAsphalt))
        self.air_TC.setText(str(conductAir))
        self.aggregate_CH.setText('Chem Aggregate')
        self.mastic_CH.setText('Chem Mastic')
        self.air_CH.setText('Chem Air')

    def runSimulation(self):
        aggregate_parameters, mastic_parameters, air_parameters = [], [], []

        aggregate_parameters.append(self.aggregate_YM.text())
        aggregate_parameters.append(self.aggregate_TC.text())
        aggregate_parameters.append(self.aggregate_CH.text())

        mastic_parameters.append(self.mastic_YM.text())
        mastic_parameters.append(self.mastic_TC.text())
        mastic_parameters.append(self.mastic_CH.text())

        air_parameters.append(self.air_YM.text())
        air_parameters.append(self.air_TC.text())
        air_parameters.append(self.air_CH.text())

        engine = SimulationEngine(aggregate_parameters, mastic_parameters,
                                  air_parameters, aw.collection)
        materials = engine.simulationCicle()

        output_results = Result(materials)
        output_results.thermalResults()


    def closeWindow(self):
        self.close()

#-----------------------------------------------------------------------------
if __name__ == '__main__':
    qApp = QtGui.QApplication(sys.argv)
    aw = ApplicationWindow()
    aw.setWindowTitle("Asphalt Mixtures Aging Simulator")
    aw.show()
    sys.exit(qApp.exec_())
    qApp.exec_()