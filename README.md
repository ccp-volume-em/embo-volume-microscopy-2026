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
    - Quantification notebooks and data: [](volseg/quantification-notebooks)
    - Human Placenta dataset: DOI pending
    - Container image: [quay.io/repository/rosalindfranklininstitute/embo-volume-segmantics-2026](https://quay.io/repository/rosalindfranklininstitute/embo-volume-segmantics-2026) (OCI Docker spec)
3. Microscopy Image Browser 3 (MIB3)
   - Container image: [quay.io/repository/rosalindfranklininstitute/mib-container](https://quay.io/repository/rosalindfranklininstitute/mib-container?tab=tags) (OCI Docker spec)
4. ilastik 1.4.2
   - Container image: [https://quay.io/repository/ccp-volume-em/ilastik](https://quay.io/repository/ccp-volume-em/ilastik?tab=tags) (ORAS Apptainer spec)
  
## Workshop Data Copy Instructions (BAND/Ada)
### BAND (in-person participants)

### Ada (online participants)

## Workshop Software Instructions (BAND/Ada)
### BAND (in-person participants)
1. Napari with plugins

    Under **Applications** in the top-left corner Select **Image Analysis > Napari**

    Example datasets should be copied from `/scratch/vEM_workshop_2026/`
    
2. Volume Segmantics
   
   - Volume Segmantics terminal: Under **Applications** Select **Image Analysis > Volseg Terminal**

     Note a copy of the default settings is located at `/scratch/vEM_Data_2026/volseg-settings`
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

    Example datasets should be copied from `/mnt/training/shared_materials`
2. Volume Segmantics
   
   - Volume Segmantics terminal: Under **Applications** Select **Software > EMBO Volseg - Terminal**
   
     A copy of the default settings is located at `/mnt/training/course_materials/volseg-settings`. The course notebooks and data can be copied from `/mnt/training/course_materials/tutorial_data/quantification-notebooks`.
   - Napari: Under **Applications** Select **Software > EMBO Volseg - Napari (0.8.0)**.
   - Jupyter Lab: Under **Applications** Select **Software > EMBO Volseg - JupyterLab**. In the terminal that opens use CTRL+Click to open the URL `http://127.0.0.1:8888/lab` for Jupyter Lab in a browser window. Select the *default* Python Notebook kernel.
3. MIB3
   
    Under **Applications** Select **Software > EMBO MIB3 (preview)**

    Example datasets should be copied from `/mnt/training/shared_materials`
4. ilastik
   
   Under **Applications** Select **Software > EMBO ilastik (1.4.2)**
