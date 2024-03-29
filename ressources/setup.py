import streamlit as st
import time
from datetime import datetime, timedelta
from dateutil import parser
from tempfile import mkstemp
from shutil import move, copymode
import os
import subprocess


st.set_page_config(
    page_title="ALD – CVD Process",
    page_icon=":hammer_and_pick:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://lmi.cnrs.fr/author/colin-bousige/',
        'Report a bug': "https://lmi.cnrs.fr/author/colin-bousige/",
        'About': """
        ## ALD – CVD Process
        Version date 2022-12-14.

        This app was made by [Colin Bousige](https://lmi.cnrs.fr/author/colin-bousige/). Contact me for support, requests, or to signal a bug.
        """
    }
)

# # # # # # # # # # # # # # # # # # # # # # # #
# Define default variables and relays
# # # # # # # # # # # # # # # # # # # # # # # #


# Relays attribution, state (NO for Normally Opened, NC for Normally Closed)
relays = {
    "V1": 1,
    "V2": 2,
    "V3": 3,
    "Ar reactor": 4,
    "Turn OFF Ar bypass": 5
}

# # # # # # # # # # # # # # # # # # # # # # # #
# Define default recipes
# # # # # # # # # # # # # # # # # # # # # # # #

recALD = {
    "recipe" : "ALD",
    "initgas": [],
    "wait"   : 10,
    "fingas" : [],
    "waitf"  : 10,
    "N"      : 100,
    "Nsteps" : 4,
    "valves" : [["Turn OFF Ar bypass", "V1", "Ar reactor"], [], ["Turn OFF Ar bypass", "V2", "Ar reactor"], []],
    "times"  : [5., 10., 5., 10.]
    }

recPurge = {
    "recipe" : "Purge",
    "initgas": [],
    "wait"   : 0,
    "fingas" : [],
    "waitf"  : 1,
    "N"      : 1,
    "Nsteps" : 1,
    "valves" : [["V1", "V2", "V3", "Ar reactor"]],
    "times"  : [180.]
    }

# For writing into the log at the end of the recipe, 
# whether it's a normal or forced ending
if 'logname' not in st.session_state:
    st.session_state['logname'] = ''
if 'start_time' not in st.session_state:
    st.session_state['start_time'] = ''
if 'cycle_time' not in st.session_state:
    st.session_state['cycle_time'] = ''

# # # # # # # # # # # # # # # # # # # # # # 
# Functions handling gas lines
# # # # # # # # # # # # # # # # # # # # # # 

def turn_ON(gas):
    """
    Switch relay from the board to turn ON gas
    """
    relnum = relays[gas]
    subprocess.run(f"usbrelay RELAY_{relnum}=1", shell=True)


def turn_OFF(gas):
    """
    Switch relay from the board to turn OFF gas
    """
    relnum = relays[gas]
    subprocess.run(f"usbrelay RELAY_{relnum}=0", shell=True)



# # # # # # # # # # # # # # # # # # # # # # 
# Functions handling log file writing/updating
# # # # # # # # # # # # # # # # # # # # # # 

def append_to_file(logfile="log.txt", text=""):
    """
    Function to easily append text to a logfile
    """
    with open(logfile, 'a') as fd:
        fd.write(f'{text}\n')


def replacement(filepath, pattern, replacement):
    """
    Function to replace a pattern in a file
    """
    # Creating a temp file
    fd, abspath = mkstemp()
    with os.fdopen(fd, 'w') as file1:
        with open(filepath, 'r') as file0:
            for line in file0:
                file1.write(line.replace(pattern, replacement))
    copymode(filepath, abspath)
    os.remove(filepath)
    move(abspath, filepath)


def update_cycle(logname, i, N):
    """
    Function to write the current cycle number in the logfile
    """
    if i == 0:
        write_to_log(logname, cycles_done=f"{i+1}/{N}")
    else:
        replacement(logname,
                    f"cycles_done      {i}/{N}",
                    f"cycles_done      {i+1}/{N}")


def write_to_log(logname, **kwargs):
    """
    Function to easily create and update a logfile
    """
    os.makedirs(os.path.dirname(logname), exist_ok=True)
    toprint = {str(key): str(value) for key, value in kwargs.items()}
    append_to_file(logname, text='\n'.join('{:15}  {}'.format(
        key, value) for key, value in toprint.items()))


def write_recipe_to_log(logname, recipe):
    """
    Function to easily create and update a logfile with a recipe
    """
    os.makedirs(os.path.dirname(logname), exist_ok=True)
    append_to_file(logname, text=f'Recipe-----------------------\n\n{recipe}')

# # # # # # # # # # # # # # # # # # # # # # 
# Functions handling UI
# # # # # # # # # # # # # # # # # # # # # # 

def framework():
    """
    Defines the style and the positions of the printing areas
    """
    global c1, c2, remcycletext, remcycle, remcyclebar, step_print
    global remtottimetext, remtottime, remtime, final_time_text, final_time
    c1, c2 = st.columns((1, 1))
    remcycletext = c1.empty()
    remcycle = c1.empty()
    remcyclebar = c1.empty()
    step_print = c1.empty()
    remtottimetext = c2.empty()
    remtottime = c2.empty()
    remtime = c2.empty()
    final_time_text = c2.empty()
    final_time = c2.empty()
    with open("ressources/style.css") as f:
        st.markdown('<style>{}</style>'.format(f.read()),
                    unsafe_allow_html=True)


def print_tot_time(tot):
    """
    Print total estimated time and estimated ending time
    """
    finaltime = datetime.now() + timedelta(seconds=tot)
    remcycletext.write("# Total Time:\n")
    tot = int(tot)
    totmins, totsecs = divmod(tot, 60)
    tothours, totmins = divmod(totmins, 60)
    tottimer = '{:02d}:{:02d}:{:02d}'.format(tothours, totmins, totsecs)
    remcycle.markdown(
        "<div><h2><span class='highlight green'>"+tottimer+"</h2></span></div>",
        unsafe_allow_html=True)
    final_time_text.write("# Ending Time:\n")
    final_time.markdown(
        "<div><h2><span class='highlight red'>"+finaltime.strftime("%H:%M") +
        "</h2></span></div>", unsafe_allow_html=True)
    remcyclebar.progress(int((0)/100))


def countdown(t, tot):
    """
    Print time countdown and total remaining time
    """
    remtottimetext.write("# Remaining Time:\n")
    tot = int(tot)
    while t>0:
        if t >= 1:
            mins, rest = divmod(t, 60)
            secs, mil = divmod(rest, 1)
            timer = '{:02d}:{:02d}:{:03d}'.format(int(mins), int(secs), int(mil*1000))
            remtime.markdown(
                f"<div><h3>Current step: <span class='highlight blue'>{timer}</h3></span></div>",
                unsafe_allow_html=True)
            totmins, totsecs = divmod(tot, 60)
            tothours, totmins = divmod(totmins, 60)
            tottimer = '{:02d}:{:02d}:{:02d}'.format(
                tothours, totmins, totsecs)
            remtottime.markdown(
                f"<div><h3>Total: <span class='highlight blue'>{tottimer}</h3></span></div>",
                unsafe_allow_html=True)
            time.sleep(1)
            t -= 1
            tot -= 1
        else:
            time.sleep(t)
            t -= 1


def showgraph(initgas=sorted(relays.keys())[0], wait=30, valves=sorted(relays.keys())[0], times=[10.],
              Nsteps=4, highlight=-1, N=100, fingas=sorted(relays.keys())[0], waitf=30):
    """
    Display a chart of the recipe
    """
    initgasclean = ' + '.join(initgas)
    if initgasclean == "":
        initgasclean = "_**No Valve Switched**_"
    fingasclean = ' + '.join(fingas)
    if fingasclean == "":
        fingasclean = "_**No Valve Switched**_"
    stepslog  = [f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**0 &bull; Initialization:** &nbsp;&nbsp;&nbsp;&nbsp;**{initgasclean}** – {wait} s<br>"]
    stepslog += [f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Repeat {N} times:**<br>"]
    stepslog += ["&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>%3d &bull; %-11s</b> – %.3lf s<br>" % \
            (i+1, ' + '.join(v) if len(v)>0 else "_**No Valve Switched**_", t) for i,(v,t) in enumerate(zip(valves,times))]
    stepslog += [f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**{Nsteps+1} &bull; Finalization:** &nbsp;&nbsp;&nbsp;&nbsp;**{fingasclean}** – {waitf} s"]
    
    annotated_steps = stepslog.copy()
    if highlight >= 0:
        if highlight>=1 and highlight<Nsteps+1:
            annotated_steps[1] = f"<span class='highlightstep green'>{annotated_steps[1]}</span>"
        annotated_steps[highlight+1 if highlight >0 else highlight] = f"<span class='highlightstep blue'>{annotated_steps[highlight+1 if highlight >0 else highlight]}</span>"
    annotated_steps = "<br><div style='line-height:35px'>" + "".join(annotated_steps)+"</div>"
    step_print.markdown(annotated_steps, unsafe_allow_html=True)


# # # # # # # # # # # # # # # # # # # # # # 
# Functions handling initialization and ending of recipe
# # # # # # # # # # # # # # # # # # # # # # 

def initialize(initgas=sorted(relays.keys())[0], wait=-1, valves=sorted(relays.keys())[0], times=[10.], 
               tot=10, N=100, fingas=sorted(relays.keys())[0], waitf=30):
    """
    Make sure the relays are closed
    """
    if len(initgas) == 0:
        for gas in sorted(relays.keys()):
            turn_OFF(gas)
    else:
        for gas in sorted(relays.keys()):
            if gas not in initgas:
                turn_OFF(gas)
            else:
                turn_ON(gas)
    if wait>0:
        showgraph(initgas=initgas, wait=wait, valves=valves, 
                  times=times, Nsteps=len(times), highlight=0, N=N, fingas=fingas, waitf=waitf)
        remcycletext.write("# Cycle number:\n")
        remcycle.markdown(f"<div><h2><span class='highlight green'>0 / {N}</h2></span></div>",
                          unsafe_allow_html=True)
        remcyclebar.progress(int((0)/N*100))
        countdown(wait, tot)


def end_recipe():
    """
    Ending procedure for recipes
    """
    subprocess.run("usbrelay RELAY_9=0", shell=True)
    st.experimental_rerun()


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#  RECIPE DEFINITIONS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

def Recipe(valves=sorted(relays.keys())[0], times=[10.], N=100, recipe="ALD", 
           initgas=sorted(relays.keys())[0], wait=30, fingas=sorted(relays.keys())[0], waitf=30):
    """
    Definition of recipe
    """
    tot = sum(times)*N+wait+waitf
    start_time = datetime.now().strftime(f"%Y-%m-%d-%H:%M:%S")
    st.session_state['start_time'] = start_time
    st.session_state['logname'] = f"Logs/{start_time}_{recipe}.txt"
    st.session_state['cycle_time'] = (tot-waitf-wait)/N
    initgasclean = ' + '.join(initgas)
    if initgasclean == "":
        initgasclean = "No Valve"
    fingasclean = ' + '.join(fingas)
    if fingasclean == "":
        fingasclean = "No Valve"
    stepslog = ["    - %-11s%.3lf s" % (' + '.join(v) if len(v)>0 else "No Valve", t) for v,t in zip(valves,times)]
    stepslog = [f"  - Init.:       {initgasclean}, {wait} s"] + stepslog
    stepslog = stepslog + [f"  - Final.:      {fingasclean}, {waitf} s"]
    stepslog = "\n"+"\n".join(stepslog)
    csv = f"""recipe|initgas|wait|fingas|waitf|N|Nsteps|valves|times
{recipe}|{",".join(initgas)}|{wait}|{",".join(fingas)}|{waitf}|{N}|{len(times)}|{",".join(";".join(v) for v in valves)}|{",".join(str(t) for t in times)}\n\nLog--------------------------\n"""
    write_recipe_to_log(st.session_state['logname'], csv)
    write_to_log(st.session_state['logname'], recipe=recipe, start=start_time,
                 steps=stepslog, N=N, time_per_cycle=timedelta(seconds=st.session_state['cycle_time']))
    initialize(initgas=initgas, wait=wait, valves=valves, times=times, 
               tot=tot, N=N, fingas=fingas, waitf=waitf)
    tot = tot - wait
    for i in range(N):
        for step in range(len(times)):
            remcycletext.write("# Cycle number:\n")
            remcycle.markdown(f"<div><h2><span class='highlight green'>{i+1} / {N}</h2></span></div>",
                                unsafe_allow_html=True)
            remcyclebar.progress(int((i+1)/N*100))
            # Steps
            for v in valves[step]:
                turn_ON(v)
            showgraph(initgas=initgas, wait=wait, valves=valves, N=N,
                      times=times, Nsteps=len(times), highlight=step+1, fingas=fingas, waitf=waitf)
            countdown(times[step], tot)
            tot = tot-times[step]
            for v in valves[step]:
                if (i<N-1 and v not in valves[(step+1)%len(times)]) or (i==N-1 and v not in fingas):
                    turn_OFF(v)
        update_cycle(st.session_state['logname'], i, N)
    showgraph(initgas=initgas, wait=wait, valves=valves, N=N,
              times=times, Nsteps=len(times), highlight=1+len(times), fingas=fingas, waitf=waitf)
    for v in fingas:
        turn_ON(v)
    remcycletext.write("# Finalization....\n")
    countdown(waitf, tot)
    end_time = datetime.now().strftime(f"%Y-%m-%d-%H:%M:%S")
    st.balloons()
    time.sleep(2)
    write_to_log(st.session_state['logname'], end=end_time,
                    duration=f"{parser.parse(end_time)-parser.parse(start_time)}",
                    ending="normal")
    end_recipe()


