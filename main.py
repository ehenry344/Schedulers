class Process:
    def __init__(self, raw_data, id):
        self.raw_data = raw_data
        self.process_id = id

        self.burst_total = sum(self.raw_data)

        # Used by scheduling algorithms

        self.burst_index = 0 #Used to keep track of which burst this process is currently on
        self.rem_burst = self.get_burst_len() #remaining time on the current burstburst (used for rr) '

        self.queue_index = 0 #which queue the process is assigned to 

        #Accounting Stuff
        self.wait_time = 0
        self.response_time = 0
        self.turnaround_time = 0

    def get_burst_len(self):
        return self.raw_data[self.burst_index]
    
    def is_complete(self):
        return self.burst_index == len(self.raw_data)-1
            
    def log(self):
        print("Process ID:", self.process_id)
        print("Raw Data:", self.raw_data)  
        print("Burst Total:", self.burst_total)
        print("Burst Index:", self.burst_index)
        print("Wait Time:", self.wait_time)
        print("Response Time:", self.response_time)
        print("Turnaround Time:", self.turnaround_time)

class ProcessCollection:
    def __init__(self, f_path):
        self.__file_path = f_path
        self.__processes = []

        self.num_processes = 0

        with open(f_path, "r") as f_obj:
            for line_num, line in enumerate(f_obj.readlines()):
                line = line[line.find("{")+1:line.find("}")]
                process = Process([int(s.strip()) for s in line.split(",")], line_num+1)

                self.__processes.append(process)
                
                self.num_processes += 1
    

    def create_copy(self): #Allows process copies to be made for e.a. scheduler 
        return ProcessCollection(self.__file_path)
    
    def get_processes(self):
        return self.__processes

    def log(self):
        for i, proc in enumerate(self.__processes):
            proc.log()
            print()

class SchedulingHandler: 
    def __init__(self, f_path, precision=2):
        self.__process_group = ProcessCollection(f_path)
        self.__output_precision = precision

        self.__ready_queues = []

        self.__pending_io = [] 
        self.__terminated = []

        self.__cpu_tick = 0 
        self.__system_tick = 0 

    @property
    def __queue_len(self): 
        total_len = 0 

        for q in self.__ready_queues: 
            total_len += len(q)

        return total_len

    # IO Logic

    def __admit_pending_io(self, pender):
        self.__pending_io.append(pender) 
        self.__pending_io.sort(key=lambda p: p[0])

    def __handle_io(self): 
        while len(self.__pending_io) != 0: 
            pending_instance = self.__pending_io.pop(0)

            if self.__queue_len == 0: 
                self.__system_tick += pending_instance[1].get_burst_len() 
            elif pending_instance[0] > self.__system_tick: 
                self.__admit_pending_io(pending_instance)
                break 

            pending_instance[1].burst_index += 1
            pending_instance[1].rem_burst = pending_instance[1].get_burst_len()

            self.__ready_queues[pending_instance[1].queue_index].append(pending_instance[1])

    # Specific Scheduler Logic 

    def __fcfs_selector(self, ready_queue): 
        return ready_queue.pop(0) 
    
    def __sjf_selector(self, ready_queue): 
        next_process = min(key=lambda p: p.get_burst_len()) # retrieves next process with shortest burst len 
        ready_queue.remove(next_process)

        return next_process
    
    # Abstract scheduler supports any non pre-emptive scheduler with a single ready queue (i.e. FCFS, SJF)

    def __step_abstract_scheduler(self, to_schedule, selector): 
        ready_queue = to_schedule # to_schedule: the group of processes that are being scheduled here

        if len(ready_queue) != 0: 
            c_process = selector(ready_queue) 

            if c_process.burst_index == 0: 
                c_process.response_time = self.__system_tick 
            
            burst_len = c_process.rem_burst 

            self.__cpu_tick += burst_len 
            self.__system_tick += burst_len 

            for p in ready_queue: p.wait_time += burst_len 

            if c_process.is_complete(): 
                c_process.turnaround_time = c_process.burst_total + c_process.wait_time 
                self.__terminated.append(c_process) 
            else: 
                c_process.burst_index += 1
                c_process.rem_burst = c_process.get_burst_len() 

                pending_instance = (c_process.rem_burst + self.__cpu_tick, c_process) 
                self.__admit_pending_io(pending_instance) 

        self.__handle_io() # check io at the end of every scheduler step 

    # Internal Scheduler Implementations Used for MLFQ 

    def __fcfs_internal(self, q_index): 
        while len(self.__ready_queues[q_index]) != 0: 
            self.__step_abstract_scheduler(self.__ready_queues[q_index], self.__fcfs_selector)
            self.__handle_io()

    def __rr_internal(self, q_index, quanta): 
        while len(self.__ready_queues[q_index]) != 0: 
            c_process = self.__ready_queues[q_index].pop(0)

            if c_process.burst_index == 0 and c_process.response_time == 0: 
                c_process.response_time = self.__system_tick 
            
            burst_length = c_process.rem_burst < quanta and c_process.rem_burst or quanta 
            c_process.rem_burst -= burst_length 

            self.__cpu_tick += burst_length 
            self.__system_tick += burst_length 

            for p in self.__ready_queues[q_index]: p.wait_time += burst_length

            if c_process.rem_burst > 0: 
                c_process.queue_index += 1
                self.__ready_queues[c_process.queue_index].append(c_process) 
            else: 
                if c_process.is_complete(): 
                    c_process.turnaround_time = c_process.burst_total + c_process.wait_time
                    self.__terminated.append(c_process) 
                else:     
                    c_process.burst_index += 1
                    
                    pending_instance = (c_process.rem_burst + self.__cpu_tick, c_process) 
                    self.__admit_pending_io(pending_instance)

            self.__handle_io() #do an io step for every step of the scheduler


    def fcfs(self): 
        #setup queue for the scheduler 
        self.__ready_queues.append([])

        for process in self.__process_group.get_processes(): 
            self.__ready_queues[0].append(process) 
        
        while len(self.__terminated) != self.__process_group.num_processes: 
            self.__step_abstract_scheduler(self.__ready_queues[0], self.__fcfs_selector) 

            self.__log_dynamic()

        print("FCFS Execution Results:")
        self.__log_terminal()

    def sjf(self):
        self.__ready_queues.append([])

        for process in self.__process_group.get_processes: 
            self.__ready_queues[0].append(process) 
        
        while len(self.__terminated) != self.__process_group.num_processes: 
            self.__step_abstract_scheduler(self.__ready_queues[0], self.__sjf_selector) 

            self.__log_dynamic()
        
        print("SJF Execution Results:")
        self.__log_terminal()

    def mlfq(self):
        self.__ready_queues = [[], [], []] 

        for process in self.__process_group.get_processes(): 
            self.__ready_queues[0].append(process) 
        
        while len(self.__terminated) != self.__process_group.num_processes: 
            self.__rr_internal(0, 5)
            self.__rr_internal(1, 10) 
            self.__fcfs_internal(2)
            
            self.__log_dynamic()
    
        print("MLFQ Execution Results:")
        self.__log_terminal()

    def __log_dynamic(self): 
        print("System Execution State")
        print("Ready Queues:") 
        
        for i, ready_queue in enumerate(self.__ready_queues): 
            print(f"Queue {i}")
            print("Contents:", [p.process_id for p in ready_queue])

        print("Pending IO:")
        print("Contents:", [p_inst[1].process_id for p_inst in self.__pending_io])

        print("CPU Tick:", self.__cpu_tick, "System Tick:", self.__system_tick)
        
        print("-------------------------------------------")

    def __log_terminal(self):
        turnaround_sum = 0 
        wait_sum = 0 
        response_sum = 0 

        self.__terminated.sort(key = lambda p: p.process_id)

        for p in self.__terminated: 
            p.log()

            turnaround_sum += p.turnaround_time 
            wait_sum += p.wait_time 
            response_sum += p.response_time 

            print()
        
        print("CPU Utilization:", round((self.__cpu_tick/self.__system_tick) * 100, self.__output_precision))
        print("Avg. Wait Time:", round(wait_sum / len(self.__terminated), self.__output_precision))
        print("Avg. Response Time:", round(response_sum / len(self.__terminated), self.__output_precision))
        print("Avg. Turnaround Time:", round(turnaround_sum / len(self.__terminated), self.__output_precision))

# Scheduling Algorithm Implementations

#Need to implement (FCFS, SJF, MLFQ)
#Calculate CPU Utilization, Waiting Times, Turnaround Times, Response Times


TEST_MODE = False 

file_path = "./process_data.txt"

if TEST_MODE: 
    file_path = "./test_process_data.txt"

main_scheduler = SchedulingHandler(file_path)
main_scheduler.mlfq()
#main_scheduler.sjf()









