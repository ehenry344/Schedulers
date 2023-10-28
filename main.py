
class Process:
    def __init__(self, raw_data, id):
        self.raw_data = raw_data
        self.process_id = id

        self.burst_total = sum(self.raw_data)

        # Used by scheduling algorithms

        self.burst_index = 0 #Used to keep track of which burst this process is currently on

        #Accounting Stuff
        self.wait_time = 0
        self.response_time = 0
        self.turnaround_time = 0

    def get_burst_len(self):
        return self.raw_data[self.burst_index]
    
    def needs_cpu(self): #Bitwise even num test
        return int(self.burst_index) & 1 == 0
    
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

    def __log_dynamic(self, ready_q, await_io, cpu_tick, sys_tick): 
        print("System Execution State")
        print("Ready Queue:") 
        print([p.process_id for p in ready_q])
        print("Awaiting IO:")
        print([p[1].process_id for p in await_io])
        print("CPU Time:", cpu_tick, "System Time:", sys_tick)
        print("-------------------------------------------")

    def __log_terminal(self, finished_processes, cpu_tick, sys_tick):
        tt_sum, wait_sum, r_sum = 0, 0, 0 

        finished_processes.sort(key=lambda p: p.process_id)

        for process in finished_processes:
            process.log()

            tt_sum += process.turnaround_time 
            wait_sum += process.wait_time
            r_sum += process.response_time

            print()
        
        print("CPU Utilization:", round((cpu_tick/sys_tick) * 100, self.__output_precision))
        print("Avg. Wait Time:", round(wait_sum / len(finished_processes), self.__output_precision))
        print("Avg. Response Time:", round(r_sum / len(finished_processes), self.__output_precision))
        print("Avg. Turnaround Time:", round(tt_sum / len(finished_processes), self.__output_precision))

    def __FCFS_internal(self, processes):
        num_processes = len(processes)

        r_queue = processes
        awaiting_io = [] 

        def insert_pending_io(re_entry_time, process):
            awaiting_io.append((re_entry_time, process))
            awaiting_io.sort(key=lambda p: p[0]) # sorts list based on process(es) io burst time

        cpu_run_time = 0
        sys_time = 0 

        terminated = []

        while len(terminated) != num_processes:
            if len(r_queue) != 0: 
                c_process = r_queue.pop(0)

                if c_process.burst_index == 0: 
                    c_process.response_time = sys_time

                #Accounting 
                burst_length = c_process.get_burst_len() 
                
                cpu_run_time += burst_length
                sys_time += burst_length

                for process in r_queue:
                    process.wait_time += burst_length

                if c_process.is_complete():
                    c_process.turnaround_time = c_process.burst_total + c_process.wait_time

                    terminated.append(c_process)

                    continue

                c_process.burst_index += 1

                insert_pending_io(c_process.get_burst_len() + cpu_run_time, c_process)

            while len(awaiting_io) != 0:
                est_re_entry, c_process = awaiting_io.pop(0)

                if len(r_queue) == 0:
                    sys_time += c_process.get_burst_len() # cpu wasn't doing anything
                elif est_re_entry > sys_time: #put back in
                    insert_pending_io(est_re_entry, c_process)
                    break 

                c_process.burst_index += 1
                r_queue.append(c_process)

            #Dynamic Execution Logging
            self.__log_dynamic(r_queue, awaiting_io, cpu_run_time, sys_time)

        return (terminated, cpu_run_time, sys_time)

    def __RR_internal(self, processes, q): #Round Robin Scheduler (q = time quantum)
        r_queue = processes 


    def sjf(self):
        group_copy = self.__process_group.create_copy()
        
        r_queue = group_copy.get_processes()
        awaiting_io = [] 
        terminated = [] 

        cpu_run_time = 0
        sys_time = 0

        def append_awaiting(re_entry_time, process):
            awaiting_io.append((re_entry_time, process)) 
            awaiting_io.sort(key=lambda elem: elem[0])

        while len(terminated) != group_copy.num_processes: 
            if len(r_queue) != 0: 
                c_process = group_copy.get_shortest_next_process() 
                
                if c_process.burst_index == 0: 
                    c_process.response_time = sys_time
                
                burst_length = c_process.get_burst_len()

                cpu_run_time += burst_length 
                sys_time += burst_length 

                group_copy.update_wait_time(burst_length)

                if c_process.is_complete(): 
                    c_process.turnaround_time = c_process.burst_total + c_process.wait_time

                    terminated.append(c_process) 
                    continue
                
                c_process.burst_index += 1 

                append_awaiting(re_entry_time=(c_process.get_burst_len() + cpu_run_time), process=c_process)

            while len(awaiting_io) != 0:
                est_re_entry, c_process = awaiting_io.pop(0)

                if len(r_queue) == 0:
                    sys_time += c_process.get_burst_len() # cpu wasn't doing anything
                elif est_re_entry > sys_time: #put back in
                    append_awaiting(re_entry_time = est_re_entry, process=c_process)
                    break 

                c_process.burst_index += 1
                r_queue.append(c_process)

            self.__log_dynamic(r_queue, awaiting_io, cpu_run_time, sys_time)

        print("SJF Execution Results:\n")
        self.__log_terminal(terminated, cpu_run_time, sys_time)

        return (terminated, cpu_run_time, sys_time)

    def mlfq(self):
        pass 

    def fcfs(self): # decorated version of FCFS 
        group_copy = self.__process_group.create_copy()
        
        terminated, cpu_tick, sys_tick = self.__FCFS_internal(group_copy.get_processes())

        print("FCFS Execution Results:\n")
        self.__log_terminal(terminated, cpu_tick, sys_tick) 



    
# Scheduling Algorithm Implementations

#Need to implement (FCFS, SJF, MLFQ)
#Calculate CPU Utilization, Waiting Times, Turnaround Times, Response Times


TEST_MODE = False 

file_path = "./process_data.txt"

if TEST_MODE: 
    file_path = "./test_process_data.txt"

main_scheduler = SchedulingHandler(file_path)
main_scheduler.fcfs()











