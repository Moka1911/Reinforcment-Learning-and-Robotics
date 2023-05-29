"""template_controller."""

# You may need to import some classes of the controller module. Ex:
#  from controller import Robot, Motor, DistanceSensor
# imported libraries
from controller import Robot
import random
import csv
import os


# Constants
MOTOR_SPEED = 4 #reflects the normal speed of the robot
DISTANCE_SENSOR_COUNT = 7 # the number of distance sensors present in the robot
GROUND_SENSOR_COUNT = 2 # the number of ground sensors present in the robot
THRESHOLD_TOUCH = 4000 # The value determines whether the robot touched an obstacle
walk_stability = 50 # counter to introduce variation in robot movements
all_possible_states = ['Dead', 'LLE', 'LLH', 'LLN', 'LLT', 'LHE', 'LHH', 'LHN', 'LHT', 'HLE', 'HLH', 'HLN', 'HLT', 'HHE', 'HHH', 'HHN', 'HHT'] #(state space)all the possible states that can be visited by the robot
all_possible_actions = ["RE","FE","CE","FH","CH","EX","RU"] #(action space)all the possible behaviours that can be executed by the robot
State_Action_possibilities_and_Qfunction = {} # A dictionary that would be used to store the possibility of execution of all actions and also the Q function of each state-action
current_state ='' # stores the current state of the robot
previous_state = '' # stores the previous state of the robot
current_action = None # stores the current behavior being executed
previous_action = None # stores the previously executed action
action_counter = 50 # determines how much time a behaviour gets executed in

#plot variables
PVE = [] # Energy Psychological Variable list
PVH = [] # Health Psychological Variable list
Ed = [] # Energy deficit list
Hd = [] # Health deficit list
Wellbeing_list = [] # Wellbeing list


#energy variables
energy_loss_rate = 0.2 # the rate of energy loss while moving
energy_gain_rate = 2.0 # the rate of energy gain when resting or consuming energy resource

energy_level = 149 # current energy psychological variable level of the robot
energy_level_optimum = 150 # optimim energy level for the robot
energy_lower_bound = 0 # lowest value of energy level
energy_upper_bound = 200 # Highest value of energy level

#health variables
damage_rate = 0.2 # the rate of health loss while in a red patch
repair_rate = 2.0 # the rate of health gain while in repair station

health = 149 # Current health value
health_optimum = 150 # Optimum health value
health_lower_bound = 0 # lowest value for health value
health_upper_bound = 200 # highest value for health value

execution_behaviour = '' # currently executed behaviour
learning_Mode = 0 # A boolean that decides if its a random start simulation (0) or learned behaviour simulation from imported csv file (1)


# create the Robot instance (taken from) (adapted from lecture materials)
robot = Robot() 

# get the time step of the current world. (adapted from lecture materials)
timestep = int(robot.getBasicTimeStep())

############ Actuators ################
def init_actuators():
    """ Initialise motors and LEDs (adapted from lecture materials)""" 
    global motor_l, motor_r, motor_speed_l, motor_speed_r, led_top, led_top_colour

    # Set up motors (adapted from lecture materials)
    motor_l = robot.getDevice('motor.left')
    motor_r = robot.getDevice('motor.right')

    # Configure motors for velocity control (adapted from lecture materials)
    motor_l.setPosition(float('inf'))
    motor_r.setPosition(float('inf'))
    
    # variables for motor values (adapted from lecture materials)
    motor_speed_l = MOTOR_SPEED
    motor_speed_r = MOTOR_SPEED

    # set up LEDs (adapted from lecture materials)
    led_top = robot.getDevice('leds.top')
    # maybe more LEDs...

    # variables for LED colour (adapted from lecture materials)
    led_top_colour = 0xff0000

def send_actuator_values():
    """ Write motor speed and LED colour variables to hardware. (adapted from lecture materials)
        Called at the end of the Main loop, after actions have been calculated """
    global motor_speed_l, motor_speed_r, led_top_colour

    motor_l.setVelocity(motor_speed_l)
    motor_r.setVelocity(motor_speed_r)
    led_top.set(led_top_colour)

def reset_motor_values():
    """ Reset motor target speed variables to zero. (adapted from lecture materials)"""
    global motor_speed_l, motor_speed_r
    
    motor_speed_l = 0
    motor_speed_r = 0


############ Sensors ################
def init_sensors():
    """ Initialise distance sensors, ground sensors etc. """
    global distance_sensors, distance_sensors_values, ground_sensors, ground_sensors_values

    # Set up distance sensors
    distance_sensors = []
    for i in range(DISTANCE_SENSOR_COUNT):
        distance_sensors_name = 'prox.horizontal.{:d}'.format(i)
        distance_sensors.append(robot.getDevice(distance_sensors_name))
        distance_sensors[i].enable(timestep)

    # Set up ground sensors
    ground_sensors = []
    for i in range(GROUND_SENSOR_COUNT):
        ground_sensors_name = 'prox.ground.{:d}'.format(i)
        ground_sensors.append(robot.getDevice(ground_sensors_name))
        ground_sensors[i].enable(timestep)

    # Create array(list) to store sensor readings
    distance_sensors_values = [0] * DISTANCE_SENSOR_COUNT
    ground_sensors_values = [0] * GROUND_SENSOR_COUNT


def read_sensors():
    """ Read sensor values from hardware into variables (adapted from lecture materials)"""
    global distance_sensors, distance_sensors_values, ground_sensors, ground_sensors_values

    for i in range(DISTANCE_SENSOR_COUNT):
        distance_sensors_values[i] = distance_sensors[i].getValue()

    for i in range(GROUND_SENSOR_COUNT):
        ground_sensors_values[i] = ground_sensors[i].getValue()

# basic functionalities
""" checks for the presence of a blue patch by using ground sensors and returns a boolean """        
def check_energy_stimulus(): 
    if int(ground_sensors_values[0]) in range(535,580) or int(ground_sensors_values[1]) in range(535,580):
        return 1
    else:
        return 0

""" checks for the presence of a green patch by using ground sensors and returns a boolean """    
def check_repair_stimulus(): 
    if int(ground_sensors_values[0]) in range(410,480) or int(ground_sensors_values[1]) in range(410,480):
        return 1
    else:
        return 0
        
""" checks for the presence of a red patch by using ground sensors and returns a boolean """    
def check_threat_stimulus(): 
    if int(ground_sensors_values[0]) in range(635,700) or int(ground_sensors_values[1]) in range(635,700):
        return 1
    else:
        return 0

#this function returns the reward of te state change in order to update the state Q function
def get_reward(previous_state,current_state):
    global previous_action
    Reward = 0
    for index in range(len(previous_state)):
        # checks if previous action is Explore and ther is an L in previous State
        if previous_action == 5 and 'L' in previous_state:
            Reward -= 4
            break
        # checks if previous action is Explore and ther is no L in previous State
        elif previous_action == 5 and not('L' in previous_state):
            Reward -= 0
            break
        # checks for presence of red patch and action previously executed at that time is runaway
        elif check_threat_stimulus() == 1 and previous_action == 6:
            Reward += 5
            break
        # checks for presence of red patch and action previously executed at that time is rest
        elif check_threat_stimulus() == 1 and previous_action == 0:
            Reward -= 5
            break
        # checks if previous state is same as current state and current state has a low psychological variable
        elif previous_state == current_state and 'L' in current_state:
            Reward -= 2
            break
        # checks if previous state is same as current state and current state has no low psychological variable        
        elif previous_state == current_state and not('L' in current_state):
            Reward += 2
            break
        # checks if single letter in previous state is same as that of current state
        elif previous_state[index] == current_state[index]:
            Reward -= 0
        # cheks if previous state letter was H and turned to L in current state
        elif previous_state[index] == 'H' and current_state[index] == 'L':
            Reward -= 5
        # cheks if previous state letter was L and turned to H in current state
        elif previous_state[index] == 'L' and current_state[index] == 'H':
            Reward += 5
        # checks if robot current state is Dead
        elif current_state == 'Dead':
            Reward -= 10
    return Reward

# used to initially set all state_action_possibilities in the dictionary to 0.142 along with its Q function to 0
def set_state_action_possibilities_and_Qfunction():
    global State_Action_possibilities_and_Qfunction
    for state in all_possible_states:
        for action in all_possible_actions:
            #skips adding state action for Dead state as it makes no sense to execute action while dead
            if state == 'Dead':
                pass
            else:
                State_Action_possibilities_and_Qfunction[state+"_"+action] = [0.142,0]    

""" used to chech whether the robot is alive or not and return a boolean based on the result """
def isAlive(): 
    global energy_level, energy_lower_bound
    if energy_level <= energy_lower_bound or health <= health_lower_bound:
        print("Thymio is dead")
        # stop the robot in case it is dead
        reset_motor_values()
        return False
    else:
        return True

# this function returns the current state of the robot as well as update the current state global value
def get_current_state():
    global current_state,energy_level,energy_level_optimum,health,health_optimum
    current_state = ''
    # this if statement determine the energy level psychological variable state
    if not(isAlive()):
         current_state = "Dead"
         return  current_state
    elif energy_level < energy_level_optimum:
        current_state += 'L'
    elif energy_level >= energy_level_optimum:
        current_state += 'H'
    
    # this if statement determine the health psychological variable state
    if not(isAlive()):
        current_state = "Dead"
        return  current_state
    elif  health < health_optimum:
        current_state += 'L'
    elif health >= health_optimum:
        current_state += 'H'
    
    # this if statement determine the presence of a stimulus or not
    if check_energy_stimulus() == 1:
        current_state += 'E'
    elif check_repair_stimulus() == 1:
        current_state += 'H'
    elif check_threat_stimulus() == 1:
        current_state += 'T'
    else:
        current_state += 'N'
    return current_state
        
 # this function is responible for updating the previous state value as well as renew the current state
def update_states():
    global current_state, previous_state
    previous_state = current_state
    current_state = get_current_state()

# this function is responible for updating the previous actin value as well as renew the current action
def update_action(next_action):
    global current_action, previous_action
    previous_action = current_action
    current_action = next_action

# this function is responsible for returning a random action based on probability chances of actions of current state
def get_randomly_selected_action():
    global State_Action_possibilities_and_Qfunction,current_state
    # getting a random number from 0 to 0.99
    random_possibility = random.uniform(0,0.99)
    implementation_action_index = 0
    # this list stores all action possibilities for current state in that order [Rest,Find_Energy, Consume_Energy, Find_Health, Consume_Health, Explore, Run_away]
    action_possibilities = []
    
    if current_state == 'Dead': return 'None'
    # retriving all possibilities of the current state
    for action in all_possible_actions:
        action_possibility = State_Action_possibilities_and_Qfunction[current_state+"_"+action][0]
        action_possibilities.append(action_possibility)
    # subtracting the random possibility by the action possibilities one by one til action possibility is bigger than random possibility
    for index in range(len(action_possibilities)):
        if random_possibility <= action_possibilities[index]:
            implementation_action_index = index
            break
        else:   
            random_possibility -= action_possibilities[index]
    return implementation_action_index
     
""" used to decrease the energy level value while the robot is moving """
def energyLoss(): 
    global energy_level
    if energy_level != 0 and energy_level > 0:
         energy_level -= energy_loss_rate
    else:
        isAlive()
        
""" used to increase the energy level value while the robot is resting or consuming energy resource """
def energyGain(): 
    global energy_level
    if energy_level != 0 and int(energy_level) in range(energy_lower_bound,energy_upper_bound):
         energy_level += energy_gain_rate
         if energy_level > energy_upper_bound:
             energy_level = energy_upper_bound
             
""" used to decrease the health level while on a red patch """
def damage(): 
    global health
    if health != 0 and health > health_lower_bound and health <= health_upper_bound:
        health -= damage_rate
    else:
        isAlive()
      
""" used to increase the health level while in a repair station """        
def repair(): 
    global health
    if health != 0 and health > health_lower_bound and health < health_upper_bound:
        health += repair_rate
        # ensures health doesnt exceed the upper bound
        if health > health_upper_bound:
            health = health_upper_bound
            
""" returns the average the ground sensors' values """ 
def ground_sensor_average(): 
    global ground_sensors, ground_sensors_values
    return (ground_sensors_values[0] + ground_sensors_values[1])//2

""" checks what type of patch is the robot stepping on and modify psychological variable accordingly """
def detectGround(): 
    global ground_sensors, ground_sensors_values, energy_level
    # checks if a blue patch is under the robot and executed action is consume energy consummatory behavior
    if int(ground_sensors_values[0]) in range(535,580) and int(ground_sensors_values[1]) in range(535,580) and current_action == 2:
        energyGain()
    # checks if a red patch is under the robot
    elif int(ground_sensors_values[0]) in range(635,700) and int(ground_sensors_values[1]) in range(635,700):
        energyLoss()
        damage()
    # checks if a green patch is under the robot and executed action is repair robot consummatory behavior
    elif int(ground_sensors_values[0]) in range(410,480) and int(ground_sensors_values[1]) in range(410,480) and current_action == 4:
        energyLoss()
        repair()
    # the robot is stepping on normal ground          
    else:
        energyLoss()


# not used in reinforced learning
""" used to calculate the motivation for each psychological variable and return the bigger motivation and behaviour """     
def motivation(): 
    global energy_level,health
    # calculate fatigue motivation
    energy_deficit = energy_level_optimum - energy_level
    energy_stimulus = check_energy_stimulus()
    energy_motivation = energy_deficit + (energy_deficit * 1.1 * energy_stimulus)
    # calculate fear motivation
    health_deficit = health_optimum - health
    health_stimulus = check_repair_stimulus()
    health_motivation = health_deficit + (health_deficit * health_stimulus)
    # if fatigue motivation wins
    if energy_motivation >= health_motivation and energy_level != energy_upper_bound:
        if energy_level < 25: # if energy level less than 25 then execute rest behaviour
            return "REST ENERGY"
        elif energy_level < energy_level_optimum and execution_behaviour == "HEALTH": # if the previous motivation was fear motivation then execute fear motivation to avoid danger
            return "HEALTH"
        elif energy_level < energy_level_optimum and execution_behaviour == "REST ENERGY": # if the previous executed behaviour was rest then continue resting till optimum level
            return "REST ENERGY"
        else:
            return "FIND ENERGY" # execute appetitive behaviour for approaching energy resources
    # if fear motivation wins
    elif health_motivation > energy_motivation:
        if energy_level < energy_level_optimum and execution_behaviour == "REST ENERGY": # if the previous executed behaviour was rest then continue resting till optimum level
            return "REST ENERGY"
        else:
            return "HEALTH" # execute fear motivation behaviour
    # if there is no motivation for fear or energy then explore the map
    else:
        return "EXPLORE"
    
    

############ Behaviours ################
""" used to make the robot walk random movements in order to explore the map"""
def behaviour_random_walk(): 
    global motor_speed_l, motor_speed_r, walk_stability
    if walk_stability < 0:
        motor_speed_l = MOTOR_SPEED + random.randint(-3,3)
        motor_speed_r = MOTOR_SPEED + random.randint(-3,3)
        walk_stability = 50
    else:
        walk_stability -= 1

""" makes the robot move using the behaviour_random_walk function while avoiding obstacles and walls"""
def behaviour_walk_avoid_walls(): 
    global distance_sensors_values, motor_speed_l, motor_speed_r
    distance_sensor_left = 4.5 * distance_sensors_values[0] + 2 * distance_sensors_values[1] + distance_sensors_values[2]
    distance_sensor_right = 5 * distance_sensors_values[4] + 2 * distance_sensors_values[3] + distance_sensors_values[2]
    # if values of left sensors is bigger than right sensors turn right
    if distance_sensor_left > THRESHOLD_TOUCH and distance_sensor_right < THRESHOLD_TOUCH:
        motor_speed_r = -MOTOR_SPEED
        motor_speed_l = MOTOR_SPEED
    # if values of right sensors is bigger than left sensors turn left
    elif distance_sensor_left < THRESHOLD_TOUCH and distance_sensor_right > THRESHOLD_TOUCH:
        motor_speed_r = -MOTOR_SPEED
        motor_speed_l = MOTOR_SPEED
    # if only left sensor ssensing object turn right
    elif distance_sensor_left > THRESHOLD_TOUCH:
        motor_speed_r = -MOTOR_SPEED
        motor_speed_l = MOTOR_SPEED
    # if only right sensor ssensing object turn left
    elif distance_sensor_right > THRESHOLD_TOUCH:
        motor_speed_r = MOTOR_SPEED
        motor_speed_l = -MOTOR_SPEED
    # no object is sensed
    else:
        behaviour_random_walk()

"""consummatory behaviour for an energy resource"""
def behaviour_consume_energy_source(): 
    global ground_sensors, ground_sensors_values, motor_speed_l, motor_speed_r,energy_level
    # if robot stepping on blue patch execute behaviour
    if int(ground_sensors_values[0]) in range(535,580) and int(ground_sensors_values[1]) in range(535,580) and energy_level != energy_upper_bound:
        speed_l = 0
        speed_r = 0
        detectGround()
        print("Recharging under progress ..... energy level =",energy_level)
        motor_speed_l = speed_l
        motor_speed_r = speed_r
    # no blue patch detected
    else:
        behaviour_walk_avoid_walls()

""" Appetitive behaviour to search for energy resource"""    
def behaviour_approach_energy_source(): 
    global ground_sensors, ground_sensors_values, motor_speed_l, motor_speed_r
    # if robot left ground sensor detect a blue patch turn to the patch
    if int(ground_sensors_values[0]) in range(535,580):
        speed_l = MOTOR_SPEED / 2
        speed_r = MOTOR_SPEED + 3 
        motor_speed_l = speed_l
        motor_speed_r = speed_r
        print("turn to energy resource")
    # if robot right ground sensor detect a blue patch turn to the patch
    elif int(ground_sensors_values[1]) in range(535,580):
        speed_r = MOTOR_SPEED / 2
        speed_l = MOTOR_SPEED + 3
        motor_speed_l = speed_l
        motor_speed_r = speed_r
        print("turn to energy resource")
    # if no blue patch was detected continue to search by walking randomly
    else:
        behaviour_walk_avoid_walls()

"""consummatory behaviour for repair stations to gain health"""
def behaviour_consummatory_repair(): 
    global ground_sensors, ground_sensors_values, motor_speed_l, motor_speed_r,health
    # if robot stepping on green patch execute behaviour
    if int(ground_sensors_values[0]) in range(410,480) and int(ground_sensors_values[1]) in range(410,480) and health != health_upper_bound:
        speed_l = 0
        speed_r = 0
        detectGround()
        print("Repairing under progress ..... health =",health)
        motor_speed_l = speed_l
        motor_speed_r = speed_r
    # no green patch detected 
    else:
        behaviour_walk_avoid_walls()

"""Appetitive behaviour to search for repair station"""
def behaviour_approach_repair_station(): 
    global ground_sensors, ground_sensors_values, motor_speed_l, motor_speed_r
    # if robot left ground sensor detect a green patch turn to the patch
    if int(ground_sensors_values[0]) in range(410,480):
        speed_l = MOTOR_SPEED / 2
        speed_r = MOTOR_SPEED + 3 
        motor_speed_l = speed_l
        motor_speed_r = speed_r
        print("turn to repair station")
    # if robot right ground sensor detect a green patch turn to the patch
    elif int(ground_sensors_values[1]) in range(410,480):
        speed_r = MOTOR_SPEED / 2
        speed_l = MOTOR_SPEED + 3
        motor_speed_l = speed_l
        motor_speed_r = speed_r
        print("turn to repair station")
    # if no green patch was detected continue to search by walking randomly
    else:
        behaviour_walk_avoid_walls()

"""Fear run away behaviour to avoid red patches """
def behaviour_runaway():  
    global ground_sensors, ground_sensors_values, motor_speed_l, motor_speed_r, health
    # if robot is stepping on a red patch runaway backwards
    if int(ground_sensors_values[0]) in range(635,700) and int(ground_sensors_values[1]) in range(635,700):
        speed_l = -MOTOR_SPEED - 3
        speed_r = -MOTOR_SPEED - 3 
        motor_speed_l = speed_l
        motor_speed_r = speed_r
        print("run away from danger")
    # if robot sesnes a red patch by left ground sensor turn to the right
    elif int(ground_sensors_values[0]) in range(635,700):
        speed_r = MOTOR_SPEED / 2
        speed_l = MOTOR_SPEED + 3 
        motor_speed_l = speed_l
        motor_speed_r = speed_r
        print("turn away from danger") 
    # if robot sesnes a red patch by right ground sensor turn to the left  
    elif int(ground_sensors_values[1]) in range(635,700):
        speed_l = MOTOR_SPEED / 2
        speed_r = MOTOR_SPEED + 3
        motor_speed_l = speed_l
        motor_speed_r = speed_r
        print("turn away from danger")

"""Consummatory rest behaviour"""
def behaviour_rest_energy(): 
    global energy_level, motor_speed_l, motor_speed_r
    # keep executing behaviour till energy at optimum level
    if energy_level < energy_level_optimum:
        motor_speed_l = 0
        motor_speed_r = 0
        energyGain()

"""Checks the action index given and executes the action accordingly along with updating value of execution behaviour global variable"""
def do_action(action_index):
    global execution_behaviour
    if action_index == 0:
        behaviour_rest_energy()
        execution_behaviour = "Rest"
    elif action_index == 1:
        behaviour_approach_energy_source()
        execution_behaviour = "Find Energy"
    elif action_index == 2:
        behaviour_consume_energy_source()
        execution_behaviour = "consume energy"
    elif action_index == 3:
        behaviour_approach_repair_station()
        execution_behaviour = "Find health"
    elif action_index == 4:
        behaviour_consummatory_repair()
        execution_behaviour = "Repair"
    elif action_index == 5:
        behaviour_walk_avoid_walls()
        execution_behaviour = "explore"
    elif action_index == 6:
        behaviour_runaway()
        execution_behaviour = "run away"

"""This function is used to deduct/add the possibility difference, resulting from upadting Q function of previous state action, from/to other actions of the previous state"""
def update_other_state_action_possibilities(sign,possibility_difference):
    global previous_state, State_Action_possibilities_and_Qfunction, previous_action,all_possible_actions
    for action in all_possible_actions:
        # if action is the behaviour previously executed skip as it has been updated in SARSA policy already
        if all_possible_actions.index(action) == previous_action:
            pass
        # if sign is negative deduct possibility difference/6 from all other action possibilities of the previous state
        elif sign == '-':
            decreased_state_action = previous_state + '_' + action
            State_Action_possibilities_and_Qfunction[decreased_state_action][0] = round(State_Action_possibilities_and_Qfunction[decreased_state_action][0] - possibility_difference / 6,3)
        # if sign is postive add possibility difference/6 to all other actions possibilities of the previous state
        elif sign == '+':
            increased_state_action = previous_state + '_' + action
            State_Action_possibilities_and_Qfunction[increased_state_action][0] = round(State_Action_possibilities_and_Qfunction[increased_state_action][0] + possibility_difference / 6,3)           

"""sets the value of the action counter based on the action being executed"""
def set_counter_value():
    global current_action, action_counter
    if current_action == 0:
        action_counter = 60
    elif current_action == 6:
        action_counter = 30
    elif current_action == 5:
        action_counter = 15
    else:
        action_counter = 40

"""This function ensures the maximum possibility of 1 is maintained due to loss of percentage while rounding up"""
def ensure_maximum_possiility():
    global previous_state, State_Action_possibilities_and_Qfunction
    possibility_list = []
    for action in all_possible_actions:
        key = previous_state + '_' + action
        # if any action possibility is less than 0 set it to 0 before adding it to possibility list
        if State_Action_possibilities_and_Qfunction[key][0] < 0: State_Action_possibilities_and_Qfunction[key][0] = 0.0
        possibility_list.append(State_Action_possibilities_and_Qfunction[key][0])
    # in case sum of all actions of the state is less than 1 divide rest of possibility on maximum possibility state actions
    if sum(possibility_list) < 1 or sum(possibility_list) < 1.0:
        difference = 1 - sum(possibility_list)
        maximum_possibility = max(possibility_list)
        
        # if there is more than one maximum possibility in list of possibilities divide possibility difference on them
        if possibility_list.count(maximum_possibility) > 1:
            index = 0
            for possibility in possibility_list:
                if possibility == maximum_possibility:
                    possibility += difference/ possibility_list.count(maximum_possibility)
                    possibility = round(possibility,3)
                    possibility_list[index] = possibility
                index += 1
        # if there is only one maximum possibility add the possibility difference to it      
        else:
            max_possibility_index = possibility_list.index(maximum_possibility)
            possibility_list[max_possibility_index] += difference
        # set State_Action_possibilities_and_Qfunction globally to the new possibilities   
        counter = 0
        for action in all_possible_actions:
            key = previous_state + '_' + action
            State_Action_possibilities_and_Qfunction[key][0] = possibility_list[counter]
            counter += 1    
        
             
    
"""This function is made for debugging purposes to print previous state along with possibilities and action of previous state actions"""        
def test_function():
    global State_Action_possibilities_and_Qfunction,previous_state,current_state
    list = [(x,y) for x,y in State_Action_possibilities_and_Qfunction.items() if previous_state in x]
    print(previous_state,list)

"""This function implements the SARSA policy for observing state, implementing action, observing new state, giving reward and updating Q function"""       
def SARSA_policy():
    global current_state,current_action,previous_action,previous_state,State_Action_possibilities_and_Qfunction,action_counter,learning_Mode
    learning_rate = 0.8
    gamma = 0.5
    do_action(current_action)
    
    # if action duration is finished
    if action_counter == 0:
        update_states() # execute function update state
        selected_action_index = get_randomly_selected_action() # get a new random action and stores it in selected_action_index
        update_action(selected_action_index) # executes update action function passing to it the newly acquired action index
        Reward = get_reward(previous_state,current_state) # reward is retieved and stored in Reward variable
        set_counter_value() # counte is set for the newly generated action
        # 'None' means the robot is dead
        if selected_action_index == 'None':
            pass
        # learning mode one means no need for updating Qfunction as this simulation is based on imported learned behaviour
        elif learning_Mode == 1:
            pass
        # update Qfunction
        else:
            previous_state_action = previous_state+'_'+all_possible_actions[previous_action] # previous state action key generated
            current_state_action = current_state+'_'+all_possible_actions[current_action] # current state action key generated
            previous_state_action_possibility , previous_Qfunction = State_Action_possibilities_and_Qfunction.get(previous_state_action) # retrieving possibility and Qfunction of previous state action
            current_state_action_possibility, current_Qfunction = State_Action_possibilities_and_Qfunction.get(current_state_action) # retrieving possibility and Qfunction of current state action
            updated_previous_Qfunction = previous_Qfunction + learning_rate * (Reward + (gamma * current_Qfunction) - previous_Qfunction ) # calculating the new Qfunction for the previous state action
            Qfunction_difference = abs(updated_previous_Qfunction - previous_Qfunction) # calculating Q function difference for possibility changes
            state_action_possibility_difference = round((Qfunction_difference * 0.06),3) # calculating the change of possibility resulted from change of Q functiion
            
            # if previous state action Q function increased then previous state-action is updated and possibility difference is deducted from other possibilities of state
            if updated_previous_Qfunction >= previous_Qfunction:
                updated_state_action_possibility = round(previous_state_action_possibility + state_action_possibility_difference,3)
                State_Action_possibilities_and_Qfunction[previous_state_action] = [updated_state_action_possibility,updated_previous_Qfunction]
                update_other_state_action_possibilities('-',state_action_possibility_difference)
                ensure_maximum_possiility()
            # if previous state action Q function decreased then previous state-action is updated and possibility difference is added to other possibilities of state  
            elif updated_previous_Qfunction < previous_Qfunction:
                updated_state_action_possibility = round(previous_state_action_possibility - state_action_possibility_difference,3)
                # if new possibility of previous state action is in negative set it to 0
                if updated_state_action_possibility < 0.0:
                    state_action_possibility_difference = state_action_possibility_difference - abs(updated_state_action_possibility)
                    updated_state_action_possibility = 0.0
                    State_Action_possibilities_and_Qfunction[previous_state_action] = [updated_state_action_possibility,updated_previous_Qfunction]
                    update_other_state_action_possibilities('+',state_action_possibility_difference)
                # if new possibility of previous state action is not negative
                else:
                    State_Action_possibilities_and_Qfunction[previous_state_action] = [updated_state_action_possibility,updated_previous_Qfunction]
                    update_other_state_action_possibilities('+',state_action_possibility_difference)
                    
                ensure_maximum_possiility()
            print("previous action:",all_possible_actions[previous_action])
            print("difference:",state_action_possibility_difference)
            print("current state:",current_state)
            test_function()
    else:
           action_counter -= 1     





# not used in reinforced learning       
""" function used to coordinate behaviours according to winning motivation returned from motivation function"""
def behaviour_coordination(): 
    global execution_behaviour
    previous_execution_behaviour = execution_behaviour
    execution_behaviour = motivation()
    # if the executed behaviour havent changed from previous time step dont print it out again
    if previous_execution_behaviour != execution_behaviour:
        print(execution_behaviour)
    # if robot is dead stop executing behaviours
    if not(isAlive()):
        execution_behaviour == "DEAD"
        pass
    # if execution behaviour is rest behaviour activate behaviour_rest_energy function
    elif execution_behaviour == "REST ENERGY":
        behaviour_rest_energy()
    # if execution behaviour is find energy activate Appetitave behaviour for energy then the consummatory behaviour
    elif execution_behaviour == "FIND ENERGY":
        behaviour_approach_energy_source()
        behaviour_consume_energy_source()
    # if execution behaviour is Health activate Appetitave behaviour for repair stations then the consummatory behaviour while executing runaway behaviour to avoid death
    elif execution_behaviour == "HEALTH":
        behaviour_runaway()
        behaviour_approach_repair_station()
        behaviour_consume_energy_source()
    # if execution behaviour is explore ,move randomly
    elif execution_behaviour == "EXPLORE":
        behaviour_walk_avoid_walls()

""" function used to record robot data during a single run in an excel file sheet"""        
def record_variables(): 
    global PVE, PVH , energy_level, health, Wellbeing_list, Ed, Hd
    # if at start of a run delete the previous run recorded data
    if execution_behaviour == "":
        if os.path.exists("data_file.csv"):
            os.remove("data_file.csv")
        if os.path.exists("learned behaviours.csv"):
            os.remove("learned behaviours.csv")
    # if the robot is alive continue to record the data
    elif isAlive():
        energy_limit =  (energy_level - energy_lower_bound) / energy_upper_bound   # calculating energy psychological variable limit    
        health_limit =  (health - health_lower_bound) / health_upper_bound # calculating health psychological variable limit 
        energy_deficit = energy_level_optimum - energy_level # calculating energy psychological variable deficit 
        health_deficit = health_optimum - health # calculating health psychological variable deficit 
        Wellbeing = (energy_limit + health_limit) / 2 # calculating Wellbeing for current psychological variables
        Wellbeing = round(Wellbeing,2) # rounding up Wellbeing value to nearest 2 decimals
        PVE.append(energy_level) # storing data
        PVH.append(health) # storing data
        Ed.append(energy_deficit) # storing data
        Hd.append(health_deficit) # storing data
        Wellbeing_list.append(Wellbeing) # storing data
        # storing data in a newly created excel file sheet named data_file.csv
        with open('data_file.csv', 'w', newline='') as write_file:
            csv_writer = csv.writer(write_file)
            for i in range(len(PVE)):
                csv_writer.writerow([PVE[i], PVH[i],Wellbeing_list[i],Ed[i],Hd[i]])
            write_file.close()
        # storing learned behaviour in a newly created excel file sheet named learned behaviours.csv   
        with open('learned behaviours.csv', 'w', newline='') as write_file:
            csv_writer = csv.writer(write_file)
            for x,y in State_Action_possibilities_and_Qfunction.items():
                csv_writer.writerow([x,y[0],y[1]])
            csv_writer.writerow(['---','---','---'])
            write_file.close()

"""This function is used to import learned behaviour from an excel sheet,
Set Learning mode and set State_Action_possibilities_and_Qfunction with imported data"""    
def get_learned_behaviours():
    global learning_Mode
    learning_Mode = 1
    read_file = open('learned behaviours 1.csv')
    csv_reader = csv.reader(read_file)
    for row in csv_reader:
        if row[0] == '---': break
        State_Action_possibilities_and_Qfunction[row[0]] = [float(row[1]),float(row[2])]
    read_file.close()
    
            
       
    

        

        
        
        

        
#
# Main entry point for code






        

# Initialisation
init_actuators()
init_sensors()
set_state_action_possibilities_and_Qfunction()
# getting current state at start of robot simulation
get_current_state()
# getting random action at start of robot simulation
current_action = get_randomly_selected_action()
#setting counter for the action
set_counter_value()
#get_learned_behaviours() #only uncomment this for importing learned behviour form external excel document
# Main loop:
# - perform simulation steps until Webots is stopping the controller
while robot.step(timestep) != -1:
    # Read the sensors:
    read_sensors()
    
    record_variables() # record data of the current time step
    
    detectGround() # modifying psychological variables according to ground sensor values and action executed
    
    SARSA_policy() # implements the reinforced learning sarsa policy
    
    # Send actuator commands:
    send_actuator_values()

    

# End of Main loop
# Exit & cleanup code.
# (none required)
