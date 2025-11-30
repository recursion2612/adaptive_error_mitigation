### IMPORTS
from qiskit.circuit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager, PassManager
from qiskit.transpiler.passes.scheduling import ALAPScheduleAnalysis, ASAPScheduleAnalysis, PadDynamicalDecoupling
from qiskit_ibm_runtime.fake_provider import FakeBrisbane 
from qiskit_ibm_runtime import EstimatorOptions, SamplerOptions, EstimatorV2 as Estimator, SamplerV2 as Sampler
from qiskit_ibm_runtime import Batch, QiskitRuntimeService
from qiskit.providers.backend import BackendV2 as Backend
from qiskit.visualization import plot_histogram
from qiskit.circuit.library import XGate 
from qiskit.quantum_info import hellinger_fidelity, SparsePauliOp
import numpy as np
import pandas as pd 
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_aer.primitives import EstimatorV2 as AerEstimator



def prepare_ghz(n_qubits: int):
    ## Prepares standard ghz state with measurements on all qubits using measure_all() 
    circuit = QuantumCircuit(n_qubits)
    circuit.h(0)
    for i in range(0, n_qubits-1):
        circuit.cx(i, i+1)

    circuit.measure_all()

    return circuit

def get_result_from_id(service, id):
    # Get Result object from service using id

    job = service.job(id)
    result = job.result()

    return result
    

### ESTIMATOR FUNCITONS FOR EXPERIMENTS



def naked_estimator(mode):
    ## Estimator with no error mitigation or supression for any mode (job, batch). ALL OPTIONS ARE DISABLED. 
    estimator_options = EstimatorOptions(default_shots=4096, seed_estimator=42069, dynamical_decoupling={"enable": False},twirling={"enable_gates": False, "enable_measure": False},resilience_level=0, resilience={"measure_mitigation":False, "zne_mitigation":False, "pec_mitigation":False}) 

    estimator = Estimator(mode=mode, options=estimator_options)
    return estimator

def noiseless_estimator_pub(actual_qubits:int, isa_circuit:QuantumCircuit, pauli="Z"):

    ## Creating Pauli Op and mapping the operator to correct qubits. Note: this can be avoided as our observable is "ZZ..Z" but still going with the procedure
    isa_observable = SparsePauliOp(pauli*actual_qubits).apply_layout(isa_circuit.layout)

    pub = (isa_circuit, isa_observable)

    return pub


def estimator_pub(isa_circuit:QuantumCircuit, isa_dd_circuit:QuantumCircuit, pauli="Z"):
    ## NOTE: isa_circuit and isa_dd_circuit must have the same no. of "actual qubit" obviously
    ## Creating Pauli Op and mapping the operator to correct qubits. 
    actual_qubits = len(isa_circuit.layout.final_index_layout())
    isa_observable    = SparsePauliOp(pauli*actual_qubits).apply_layout(isa_circuit.layout)
    isa_dd_observable = SparsePauliOp(pauli*actual_qubits).apply_layout(isa_dd_circuit.layout)
    

    pub = [(isa_circuit, isa_observable), (isa_dd_circuit, isa_dd_observable)]

    return pub





def pm_for_backend(bknd: Backend, opt_level, seed=42069):
    ## Returns a PassManager from generate_preset_pass_manager for given opt_level and backend(bknd)
    pm = generate_preset_pass_manager(optimization_level=opt_level, backend=bknd, seed_transpiler=seed)
    return pm


def prepare_dd_pm(backend: Backend, scheduling_method="alap", seq=[XGate(), XGate()]):
    ## Returns a PassManager for DD with customizable DD sequence and scheduelling method. 
    
    target = backend.target
    ## Prepare a preset passmanager for backend optimization_level=3
    pm = pm_for_backend(bknd=backend, opt_level=3, seed=42069)

    if scheduling_method == "alap":
        pm.scheduling.append(ALAPScheduleAnalysis(target=target))
        pm.scheduling.append(PadDynamicalDecoupling(target=target, dd_sequence=seq))

    elif scheduling_method == "asap":
        pm.scheduling.append(ASAPScheduleAnalysis(target=target))
        pm.scheduling.append(PadDynamicalDecoupling(target=target, dd_sequence=seq))
        
    return pm



def estimator_execute_on_hardware(bknd :Backend , estimator_pub):
    ## Batch mode execution of quantum circuits on hardware
    
    with Batch(backend=bknd) as batch:
        estimator = naked_estimator(mode=batch)
        job = estimator.run(estimator_pub)
        id = job.job_id()
        print(id)
    return id
    


### SAMPLER FUNCTIONS FOR EXPERIMENTS


def naked_sampler(mode, shots=4096):
    ## Sampler with no error mitigation or supression for any mode (job, batch). ALL OPTIONS ARE DISABLED. 
    options = SamplerOptions(default_shots=shots, dynamical_decoupling={"enable": False}, twirling={"enable_gates": False, "enable_measure": False})
    sampler = Sampler(mode=mode, options=options)
    return sampler



def execute_on_hardware(bknd, sampler_pub):
    ## Batch mode execution of quantum circuits on hardware
    with Batch(backend=bknd) as batch:
        sampler = naked_sampler(mode=batch, shots=4096)
        job = sampler.run(sampler_pub)
        id = job.job_id()
        print(id)
    return id


def get_fidelity_for_circuit(ideal=dict, simulated=dict, no_dd_counts=dict, dd_counts=dict):

    ## Returns List[List] of hellinger fidelity results. Outer list is of length 2 and contains
    # 0 :- List of len 3 with hellinger fidelity compared to ideal counts. [hellinger_simulated, hellinger_no_dd, hellinger_dd]
    # 1 :- List of len 2 with hellinger fidelity compared to simulated counts. [hellinger_no_dd, hellinger_dd]

    # Calculating hellinger fidelity compared to ideal counts

    hellinger_results = []

    for target_result in [simulated, no_dd_counts, dd_counts]:

        hellinger_results.append(hellinger_fidelity(ideal, target_result))

    # Calculate hellinger fidelity compared to simulated counts

    alt_hellinger_results = []

    for target_result in [no_dd_counts, dd_counts]:
        alt_hellinger_results.append(hellinger_fidelity(simulated, target_result))



    return [hellinger_results, alt_hellinger_results]