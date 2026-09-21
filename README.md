# EMBO Volume Microscopy 2026
This repository contains container build files and instructions for 
software used during the September 2026 EMBO Practical Course 
*Advanced analysis and processing of volume electron microscopy data.*

## Software Deployed
1. Napari 0.6.6 (Python 3.11) with plugins stitcher, pystackreg, careamics, convpaint, clusters-plotter, skimage-regionprops, apoc, skimage, micro-sam, skan, empanada and zelda
    - Course datasets: https://zenodo.org/records/18187789, https://zenodo.org/records/15311513 and https://zenodo.org/records/22202983
    - NucleoNet model: https://zenodo.org/records/18142651
    - DropNet model: https://zenodo.org/records/15298854
    - Container image: [quay.io/rosalindfranklininstitute/embo-napari-workshop-2026](https://quay.io/repository/rosalindfranklininstitute/embo-napari-workshop-2026) (ORAS Apptainer spec)
2. Volume Segmantics 0.4.0 (Python 3.11) with standalone Napari and Jupyter Lab
    - Quantification notebooks and data: [volseg/quantification-notebooks](volseg/quantification-notebooks)
    - Human Placenta dataset: https://www.ebi.ac.uk/empiar/EMPIAR-13952/
    - Container image: [quay.io/repository/rosalindfranklininstitute/embo-volume-segmantics-2026](https://quay.io/repository/rosalindfranklininstitute/embo-volume-segmantics-2026) (OCI Docker spec)
3. Microscopy Image Browser 3 (MIB3)
   - Container image: [quay.io/repository/rosalindfranklininstitute/mib-container](https://quay.io/repository/rosalindfranklininstitute/mib-container?tab=tags) (OCI Docker spec)
4. ilastik 1.4.2
   - Container image: [https://quay.io/repository/ccp-volume-em/ilastik](https://quay.io/repository/ccp-volume-em/ilastik?tab=tags) (ORAS Apptainer spec)

## Workshop Access Instructions
### BAND (in-person participants)
Access: https://band.vm.fedcloud.eu/#/eosc-landingpage

Log in with a Google Account (recommended), select **1 GPU**, and **Create Desktop**. If creation fails, remove the desktop and retry.

**Known bug:** if a large grey error dialogue appears during a session, notify an instructor - an administrator will resolve it.

### Ada (online participants)
A sign-up link will be sent to you via email or shared directly during the workshop. Enter your email on the sign-up page and you'll receive a unique URL by email to access the course, where you can create a new workspace.
   
## Workshop Data Copy Instructions (BAND/Ada)
### BAND (in-person participants)
All tutorial data is stored in `/scratch/vEM_workshop_2026/`.

To copy it to your home directory:
1. Open the file manager (**Home** icon on Desktop), go to **Other locations > scratch**.
2. Open a second file manager window via **Home**.
3. Right-click **vEM_workshop_2026** in the first window, *Copy*, then *Paste* into the second.

### Ada (online participants)
All tutorial data is stored in `/mnt/training/course_materials/vEM_workshop_2026/`. 

*This should be copied to your home directory automatically when you create a workspace.* 
In case it does not, you can perform a manual copy:
1. Open the file manager (**Applications > System > File Manger**), select **Devices > training** and then **course_materials**.
2. Open a second file manager window (**Applications > System > File Manger**).
3. Right-click **vEM_workshop_2026** in the first window, *Copy*, then *Paste* into the second.

## Workshop Software Instructions (BAND/Ada)
### BAND (in-person participants)
1. Napari with plugins

    Under **Applications** in the top-left corner Select **Image Analysis > Napari**
    
2. Volume Segmantics
   
   - Volume Segmantics terminal: Under **Applications** Select **Image Analysis > Volseg Terminal**

   - Napari: Same as 1.
   - Jupyter Lab: Under **Applications** Select **Programming > JupyterLab**. Select the **Volume Segmnatics** Notebook kernel.
3. MIB3
   
    Under **Applications** Select **Image Analysis > MIB3**
    
    Example datasets should be copied from `/scratch/`
4. ilastik
   
   Under **Applications** Select **Image Analysis > ilastik**

### Ada (online participants)
Note you can get to course data quickly by selecting **training** in the file manager (**Applications > System > File Manager**) or **Data** in the start menu.

1. Napari with plugins
   
    Under **Applications** in the bottom-left corner Select **Software > EMBO Napari (0.6.6)**

2. Volume Segmantics
   
   - Volume Segmantics terminal: Under **Applications** Select **Software > EMBO Volseg - Terminal**
   
   - Napari: Under **Applications** Select **Software > EMBO Volseg - Napari (0.8.0)**.
   - Jupyter Lab: Under **Applications** Select **Software > EMBO Volseg - JupyterLab**. In the terminal that opens use CTRL+Click to open the URL `http://127.0.0.1:8888/lab` for Jupyter Lab in a browser window. Select the *default* Python Notebook kernel.
3. MIB3
   
    Under **Applications** Select **Software > EMBO MIB3 (preview)**

4. ilastik
   
   Under **Applications** Select **Software > EMBO ilastik (1.4.2)**
