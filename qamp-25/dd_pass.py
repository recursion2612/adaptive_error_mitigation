from qiskit.converters import circuit_to_dag
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT, XGate
from qiskit_ibm_runtime.fake_provider import FakeTorino
from qiskit.transpiler import generate_preset_pass_manager, PassManager
from qiskit.transpiler.passes.scheduling import ALAPScheduleAnalysis, PadDynamicalDecoupling
import time 


NUM_QUBITS = 4

circuit = QFT(num_qubits=NUM_QUBITS)

circuit.compose(QFT(num_qubits=NUM_QUBITS, inverse=True), inplace=True)
circuit = circuit.decompose()


ftorino = FakeTorino()

pm = generate_preset_pass_manager(backend=ftorino, optimization_level=2)

start = time.time()
opt_circuit = pm.run(circuit)
stop = time.time() - start
target = ftorino.target

print(f"pre-dd transpilation time= {stop}")

X = XGate()
 
dd_sequence = [X, X]

dd_alap_pm = PassManager(
    [
        ALAPScheduleAnalysis(target=target),
        PadDynamicalDecoupling(target=target, dd_sequence=dd_sequence),
    ]
)


# opt_dag = circuit_to_dag(opt_circuit)
# opt_dag.draw(filename="dag_dd.png");
start2 = time.time()
dd_circuit = dd_alap_pm.run(opt_circuit)
stop2 = time.time() - start2

print(f"dd transpilation time= {stop2}")

