# EMBO Volume Microscopy 2026
This repository contains container build files and instructions for 
software used during the September 2026 EMBO Practical Course 
*Advanced analysis and processing of volume electron microscopy data.*

## Software Deployed
1. Napari 0.6.6 (Python 3.11) with plugins stitcher, pystackreg, careamics, convpaint, clusters-plotter, skimage-regionprops, apoc, skimage, micro-sam, skan, empanada and zelda
> Container image: [quay.io/rosalindfranklininstitute/embo-napari-workshop-2026](https://quay.io/repository/rosalindfranklininstitute/embo-napari-workshop-2026) (ORAS Apptainer spec)

2. Volume Segmantics 0.4.0 (Python 3.11) with standalone Napari and Jupyter Lab
> Container image: [quay.io/repository/rosalindfranklininstitute/embo-volume-segmantics-2026](https://quay.io/repository/rosalindfranklininstitute/embo-volume-segmantics-2026) (OCI Docker spec)

3. Microscopy Image Browser 3 (MIB3)
> Container image: [quay.io/repository/rosalindfranklininstitute/mib-container](https://quay.io/repository/rosalindfranklininstitute/mib-container?tab=tags) (OCI Docker spec)

4. ilastik 1.4.2
> Container image: [https://quay.io/repository/ccp-volume-em/ilastik](https://quay.io/repository/ccp-volume-em/ilastik?tab=tags)

## Workshop Instructions (BAND/Ada)
### BAND (in-person participants)
1. Napari with plugins
   
   Under **Applications** in the top-left corner Select **Image Analysis > Napari**
2. Volume Segmantics
   
   - Volume Segmantics terminal: Under **Applications** Select **Image Analysis > Volseg Terminal**

     Note a copy of the default settings is located at `/scratch/vEM_Data_2026/volseg-settings`
   - Napari: Same as 1.
   - Jupyter Lab: Under **Applications** Select **Programming > JupyterLab**. Select the **Volume Segmnatics** Notebook kernel.
3. MIB3
   
   Under **Applications** Select **Image Analysis > MIB3**
5. ilastik
   
   Under **Applications** Select **Image Analysis > ilastik**

### Ada (online participants)
1. Napari with plugins
   
   Under **Applications** in the bottom-left corner Select **Software > EMBO Napari (0.6.6)**
2. Volume Segmantics
   
   - Volume Segmantics terminal: Under **Applications** Select **Software > EMBO Volseg - Terminal**
   
     Note a copy of the default settings is located at `/opt/volseg-settings`
   - Napari: Under **Applications** Select **Software > EMBO Volseg - Napari (0.8.0)**.
   - Jupyter Lab: Under **Applications** Select **Software > EMBO Volseg - JupyterLab**. In the terminal that opens use CTRL+Click to open the URL `http://127.0.0.1:8888/lab` for Jupyter Lab in a browser window. Select the *default* Python Notebook kernel.
3. MIB3
   
   Under **Applications** Select **Software > EMBO MIB3 (preview)**
   
   In order to use the Segment Anything Model 2 (SAM2) tool, you will need to
configure:

   - **Preferences > External Directories**: Chose Python installation path
          `/opt/miniconda/envs/sam4mib/bin/python3.11` (in the file picker you may need to toggle the type of files to 'All types' to see `python3.11`)
   - Select the Segment Anything Model 2 tool for bottom left pane, select
          SAM2 and press the Settings Cog Icon. Under PATH to segment-anything-2 input `/opt/segment-anything-2`
   
    Note a prompt may appear asking you to download model files. Press Continue with download.
5. ilastik
   
   Under **Applications** Select **Software > EMBO ilastik (1.4.2)**
