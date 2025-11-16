from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager, PassManager
from qiskit.transpiler.passes.scheduling import ALAPScheduleAnalysis, ASAPScheduleAnalysis, PadDynamicalDecoupling

import pandas as pd

def prepare_ghz(n_qubits:int):
    circuit = QuantumCircuit(n_qubits)
    circuit.h(0)
    for i in range(0, n_qubits-1):
        circuit.cx(i, i+1)

    circuit.measure_all()

    return circuit



def execute_on_noisy_backend(transpiled_circuit:QuantumCircuit, noise_model, simulator=AerSimulator()):
    job = simulator.run(transpiled_circuit, shots=1024*10, noise_model=noise_model)
    result = job.result().get_counts()

    return result




def from_counts_to_probabilities(counts_dict:dict):
    
    total = sum(counts_dict.values())
    prob_dict = dict()
    for k in counts_dict:
        prob_dict[k] = counts_dict[k]/total

    return prob_dict



def generate_experiment(num_qubits, fake_backend, schedule):
    circuit = prepare_ghz(num_qubits)

    pm = generate_preset_pass_manager(optimization_level=3, seed_transpiler=42, backend=fake_backend)

    transpiled_circuit = pm.run(circuit)

    from qiskit.circuit.library import XGate

    dd_sequence = [XGate(), XGate()]

    if schedule == 'asap':
        from qiskit.transpiler.passes.scheduling import ASAPScheduleAnalysis
        dd_pm = PassManager(
        [
            ASAPScheduleAnalysis(target=fake_backend.target),
            PadDynamicalDecoupling(target=fake_backend.target, dd_sequence=dd_sequence),
        ])

        dd_transpiled_circuit = dd_pm.run(transpiled_circuit)



    elif schedule=='alap':
        from qiskit.transpiler.passes.scheduling import ALAPScheduleAnalysis
        dd_pm = PassManager(
        [
            ALAPScheduleAnalysis(target=fake_backend.target),
            PadDynamicalDecoupling(target=fake_backend.target, dd_sequence=dd_sequence),
        ])

        dd_transpiled_circuit = dd_pm.run(transpiled_circuit)

    else:
        dd_transpiled_circuit = transpiled_circuit


    noise_model = NoiseModel.from_backend(fake_backend)

    res_dict = execute_on_noisy_backend(dd_transpiled_circuit, noise_model)

    return from_counts_to_probabilities(res_dict)



    

from qiskit_ibm_runtime.fake_provider import FakeSherbrooke, FakeBrisbane, FakeTorino

backends = {"ftorino":FakeTorino(), "fbrisbane":FakeBrisbane(), "fsherbrooke":FakeSherbrooke()}

methods = ['', 'alap', 'asap']

def metric_ghz(input_dict):
    num_qubit = len(list(input_dict.keys())[0]) 
    
    metric = input_dict['0'*num_qubit] + input_dict['1'*num_qubit]
    return metric


score_dict_list = []

for n in range(3, 20):
    exp_result_dict = dict()
    for backend in backends.keys():

        result_dict_list = []

        score_list = []

        for method in methods:
            print(f"Generating results for {n}-qubit GHZ state on {backend} backend with {method} schedueling")
            res_prob = generate_experiment(n, backends[backend], method)

            result_dict_list.append(res_prob)

            score = metric_ghz(res_prob)
            score_list.append(score)

            print(f"Score = {score}")

        exp_result_dict[backend] = tuple(score_list)

        result_df = pd.DataFrame(result_dict_list, index=methods)
        result_df.fillna(0, inplace=True)

        csv_filename = f"GHZ-{n}-{backend}-XX-DD.csv"

        result_df.to_csv(csv_filename)
        print(f"Results saved as {csv_filename}")

    
    score_dict_list.append(exp_result_dict)



score_df = pd.DataFrame(score_dict_list, index=[i for i in range(3, 20)])

score_df.to_csv("GHZ-3-20-score-for-DD.csv")







            

    
