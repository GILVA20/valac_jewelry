import ast
import os
from graphviz import Digraph

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.functions = []  # Almacena las funciones encontradas
        self.calls = []      # Almacena las llamadas a funciones
        self.states = []     # Almacena estados (condiciones, bucles)
        self.current_function = None  # Función actual que se está analizando

    def visit_FunctionDef(self, node):
        """Visita las definiciones de funciones y las almacena."""
        self.current_function = node.name
        self.functions.append(node.name)
        self.generic_visit(node)
        self.current_function = None

    def visit_Call(self, node):
        """Visita las llamadas a funciones y las almacena."""
        if isinstance(node.func, ast.Name):
            # Llamadas simples a funciones (ej: funcion())
            self.calls.append((self.current_function, node.func.id))
        elif isinstance(node.func, ast.Attribute):
            # Llamadas a métodos de objetos (ej: objeto.metodo())
            self.calls.append((self.current_function, node.func.attr))
        self.generic_visit(node)

    def visit_If(self, node):
        """Visita las condiciones if y las almacena como estados."""
        self.states.append((self.current_function, "If Condition"))
        self.generic_visit(node)

    def visit_For(self, node):
        """Visita los bucles for y los almacena como estados."""
        self.states.append((self.current_function, "For Loop"))
        self.generic_visit(node)

    def visit_While(self, node):
        """Visita los bucles while y los almacena como estados."""
        self.states.append((self.current_function, "While Loop"))
        self.generic_visit(node)

def analyze_code(file_path):
    """Analiza un archivo de código y devuelve un objeto CodeAnalyzer."""
    with open(file_path, "r", encoding="utf-8") as file:
        tree = ast.parse(file.read(), filename=file_path)
    analyzer = CodeAnalyzer()
    analyzer.visit(tree)
    return analyzer

def generate_architecture_diagram(analyzer, output_file):
    """Genera un diagrama de arquitectura."""
    dot = Digraph(comment="Architecture Diagram")
    
    # Añadir nodos para cada función
    for function in set(analyzer.functions):
        dot.node(function, function)
    
    # Añadir aristas para las llamadas entre funciones
    for caller, callee in analyzer.calls:
        if callee in analyzer.functions:
            dot.edge(caller, callee)
    
    # Guardar y renderizar el diagrama
    dot.render(output_file, format="png", cleanup=True)
    print(f"Diagrama de arquitectura guardado como {output_file}.png")

def generate_state_diagram(analyzer, output_file):
    """Genera un diagrama de estados."""
    dot = Digraph(comment="State Diagram")
    
    # Añadir nodos para cada estado
    states = set(analyzer.states)
    for function, state in states:
        dot.node(f"{function}: {state}", f"{function}: {state}")
    
    # Añadir aristas para las transiciones entre estados
    for i in range(len(analyzer.states) - 1):
        current_state = f"{analyzer.states[i][0]}: {analyzer.states[i][1]}"
        next_state = f"{analyzer.states[i + 1][0]}: {analyzer.states[i + 1][1]}"
        dot.edge(current_state, next_state)
    
    # Guardar y renderizar el diagrama
    dot.render(output_file, format="png", cleanup=True)
    print(f"Diagrama de estados guardado como {output_file}.png")

def main():
    # Ruta al directorio de código (valac_jewelry dentro de valacjoyas)
    code_directory = os.path.join("valacjoyas", "valac_jewelry")
    output_architecture = "architecture_diagram"
    output_state = "state_diagram"

    all_functions = []
    all_calls = []
    all_states = []

    # Recorrer todos los archivos Python en el directorio
    for root, dirs, files in os.walk(code_directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                print(f"Analizando archivo: {file_path}")
                analyzer = analyze_code(file_path)
                all_functions.extend(analyzer.functions)
                all_calls.extend(analyzer.calls)
                all_states.extend(analyzer.states)

    # Combinar resultados de todos los archivos
    combined_analyzer = CodeAnalyzer()
    combined_analyzer.functions = list(set(all_functions))  # Eliminar duplicados
    combined_analyzer.calls = list(set(all_calls))          # Eliminar duplicados
    combined_analyzer.states = list(set(all_states))        # Eliminar duplicados

    # Generar diagramas
    generate_architecture_diagram(combined_analyzer, output_architecture)
    generate_state_diagram(combined_analyzer, output_state)

if __name__ == "__main__":
    main()