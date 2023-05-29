"""template_controller."""

# You may need to import some classes of the controller module. Ex:
#  from controller import Robot, Motor, DistanceSensor
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

#plot variables
PVE = [] # Energy Psychological Variable list
PVH = [] # Health Psychological Variable list
Ed = [] # Energy deficit list
Hd = [] # Health deficit list
Wellbeing_list = [] # Wellbeing list


#energy variables
energy_loss_rate = 0.5 # the rate of energy loss while moving
energy_gain_rate = 2.0 # the rate of energy gain when resting or consuming energy resource

energy_level = 100 # current energy psychological variable level of the robot
energy_level_optimum = 150 # optimim energy level for the robot
energy_lower_bound = 0 # lowest value of energy level
energy_upper_bound = 200 # Highest value of energy level

#health variables
damage_rate = 0.5 # the rate of health loss while in a red patch
repair_rate = 2.0 # the rate of health gain while in repair station

health = 100 # Current health value
health_optimum = 150 # Optimum health value
health_lower_bound = 0 # lowest value for health value
health_upper_bound = 200 # highest value for health value


execution_behaviour = "" # used to keep track of the current executed behaviour



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
""" used to chech whether the robot is alive or not and return a boolean based on the result """
def isAlive(): 
    global energy_level, energy_lower_bound
    if energy_level <= energy_lower_bound or health <= health_lower_bound:
        print("Thymio is dead")
        reset_motor_values()
        return False
    else:
        return True
        
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
    # checks if a blue patch is under the robot
    if int(ground_sensors_values[0]) in range(535,580) and int(ground_sensors_values[1]) in range(535,580):
        energyGain()
    # checks if a red patch is under the robot
    elif int(ground_sensors_values[0]) in range(635,700) and int(ground_sensors_values[1]) in range(635,700):
        energyLoss()
        damage()
    # checks if a green patch is under the robot  
    elif int(ground_sensors_values[0]) in range(410,480) and int(ground_sensors_values[1]) in range(410,480):
        energyLoss()
        repair()
    # the robot is stepping on normal ground          
    else:
        energyLoss()

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
    # if robot stepping on blue patch execute consummatory behaviour
    if int(ground_sensors_values[0]) in range(535,580) and int(ground_sensors_values[1]) in range(535,580):
        behaviour_consume_energy_source()
    # if robot left ground sensor detect a blue patch turn to the patch
    elif int(ground_sensors_values[0]) in range(535,580):
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
    # if robot stepping on green patch execute consummatory behaviour
    if int(ground_sensors_values[0]) in range(410,480) and int(ground_sensors_values[1]) in range(410,480):
        behaviour_consume_energy_source()
    # if robot left ground sensor detect a green patch turn to the patch
    elif int(ground_sensors_values[0]) in range(410,480):
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
    # if the robot is alive continue to record the data
    elif isAlive():
        energy_limit =  energy_level - energy_lower_bound   # calculating energy psychological variable limit    
        health_limit =  health - health_lower_bound # calculating health psychological variable limit 
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
        
        
    

        

        
        
        

        
#
# Main entry point for code






        

# Initialisation
init_actuators()
init_sensors()
# Main loop:
# - perform simulation steps until Webots is stopping the controller
while robot.step(timestep) != -1:
    # Read the sensors:
    read_sensors()
    
    record_variables() # record data of the current time step
    
    detectGround() # modifying psychological variables according to ground sensor values
    
    # Behaviours...
    behaviour_coordination() # executing the suitable behaviour for current motivation
    
    isAlive() # checkign if robot is still alive
    
    print(energy_level,health) # printing out energy level and health value
    # Send actuator commands:
    send_actuator_values()

# End of Main loop
# Exit & cleanup code.
# (none required)
