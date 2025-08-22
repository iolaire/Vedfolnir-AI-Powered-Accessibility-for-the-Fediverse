# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
API Documentation Generator

This script extracts function and class signatures from Python source files
and generates comprehensive API documentation with usage examples.
"""

import ast
import os
import sys
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import inspect
import importlib.util

@dataclass
class FunctionSignature:
    """Represents a function signature with metadata"""
    name: str
    args: List[str]
    defaults: List[Any]
    return_annotation: Optional[str]
    docstring: Optional[str]
    is_async: bool
    is_method: bool
    is_classmethod: bool
    is_staticmethod: bool
    decorators: List[str]

@dataclass
class ClassSignature:
    """Represents a class signature with metadata"""
    name: str
    bases: List[str]
    docstring: Optional[str]
    methods: List[FunctionSignature]
    properties: List[str]
    class_variables: List[str]
    decorators: List[str]

@dataclass
class ModuleSignature:
    """Represents a module signature with metadata"""
    name: str
    path: str
    docstring: Optional[str]
    functions: List[FunctionSignature]
    classes: List[ClassSignature]
    imports: List[str]
    constants: List[str]

class APIDocumentationGenerator:
    """Generates comprehensive API documentation from Python source files"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.modules: Dict[str, ModuleSignature] = {}
        
    def extract_module_signature(self, file_path: Path) -> ModuleSignature:
        """Extract signature information from a Python module"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            # Extract module docstring
            module_docstring = ast.get_docstring(tree)
            
            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
            
            # Extract constants (module-level assignments)
            constants = []
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            constants.append(target.id)
            
            # Extract functions and classes
            functions = []
            classes = []
            
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    func_sig = self._extract_function_signature(node)
                    functions.append(func_sig)
                elif isinstance(node, ast.ClassDef):
                    class_sig = self._extract_class_signature(node)
                    classes.append(class_sig)
            
            relative_path = file_path.relative_to(self.project_root)
            module_name = str(relative_path).replace('/', '.').replace('\\', '.').replace('.py', '')
            
            return ModuleSignature(
                name=module_name,
                path=str(file_path),
                docstring=module_docstring,
                functions=functions,
                classes=classes,
                imports=imports,
                constants=constants
            )
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None
    
    def _extract_function_signature(self, node: ast.FunctionDef) -> FunctionSignature:
        """Extract function signature from AST node"""
        # Extract arguments
        args = []
        defaults = []
        
        # Regular arguments
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)
        
        # Default values
        if node.args.defaults:
            defaults = [ast.unparse(default) for default in node.args.defaults]
        
        # Keyword-only arguments
        if node.args.kwonlyargs:
            args.append("*")
            for arg in node.args.kwonlyargs:
                arg_str = arg.arg
                if arg.annotation:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                args.append(arg_str)
        
        # Variable arguments
        if node.args.vararg:
            arg_str = f"*{node.args.vararg.arg}"
            if node.args.vararg.annotation:
                arg_str += f": {ast.unparse(node.args.vararg.annotation)}"
            args.append(arg_str)
        
        # Keyword arguments
        if node.args.kwarg:
            arg_str = f"**{node.args.kwarg.arg}"
            if node.args.kwarg.annotation:
                arg_str += f": {ast.unparse(node.args.kwarg.annotation)}"
            args.append(arg_str)
        
        # Return annotation
        return_annotation = None
        if node.returns:
            return_annotation = ast.unparse(node.returns)
        
        # Docstring
        docstring = ast.get_docstring(node)
        
        # Decorators
        decorators = []
        for decorator in node.decorator_list:
            decorators.append(ast.unparse(decorator))
        
        # Check for method types
        is_method = len(args) > 0 and args[0] in ['self', 'cls']
        is_classmethod = 'classmethod' in decorators
        is_staticmethod = 'staticmethod' in decorators
        
        return FunctionSignature(
            name=node.name,
            args=args,
            defaults=defaults,
            return_annotation=return_annotation,
            docstring=docstring,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=is_method,
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod,
            decorators=decorators
        )
    
    def _extract_class_signature(self, node: ast.ClassDef) -> ClassSignature:
        """Extract class signature from AST node"""
        # Base classes
        bases = []
        for base in node.bases:
            bases.append(ast.unparse(base))
        
        # Docstring
        docstring = ast.get_docstring(node)
        
        # Methods and properties
        methods = []
        properties = []
        class_variables = []
        
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_sig = self._extract_function_signature(item)
                if 'property' in method_sig.decorators:
                    properties.append(method_sig.name)
                else:
                    methods.append(method_sig)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_variables.append(target.id)
        
        # Decorators
        decorators = []
        for decorator in node.decorator_list:
            decorators.append(ast.unparse(decorator))
        
        return ClassSignature(
            name=node.name,
            bases=bases,
            docstring=docstring,
            methods=methods,
            properties=properties,
            class_variables=class_variables,
            decorators=decorators
        )
    
    def scan_project(self, exclude_patterns: List[str] = None) -> None:
        """Scan the entire project for Python files and extract signatures"""
        if exclude_patterns is None:
            exclude_patterns = [
                '__pycache__',
                '.git',
                '.pytest_cache',
                'venv',
                'env',
                '.venv',
                'node_modules',
                'migrations/versions',  # Exclude auto-generated migration files
                'tests/fixtures',       # Exclude test fixtures
            ]
        
        for py_file in self.project_root.rglob('*.py'):
            # Skip excluded patterns
            if any(pattern in str(py_file) for pattern in exclude_patterns):
                continue
            
            module_sig = self.extract_module_signature(py_file)
            if module_sig:
                self.modules[module_sig.name] = module_sig
    
    def generate_markdown_documentation(self, output_dir: Path) -> None:
        """Generate markdown documentation for all modules"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate index file
        self._generate_index_file(output_dir)
        
        # Generate documentation for each module
        for module_name, module_sig in self.modules.items():
            self._generate_module_documentation(module_sig, output_dir)
    
    def _generate_index_file(self, output_dir: Path) -> None:
        """Generate index file with all modules"""
        index_path = output_dir / 'index.md'
        
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("# API Documentation Index\n\n")
            f.write("This is an auto-generated index of all modules in the Vedfolnir project.\n\n")
            
            # Group modules by category
            categories = {
                'Core Modules': [],
                'Security Modules': [],
                'Utility Modules': [],
                'Test Modules': [],
                'Script Modules': [],
                'Other Modules': []
            }
            
            for module_name, module_sig in sorted(self.modules.items()):
                if 'security' in module_name:
                    categories['Security Modules'].append((module_name, module_sig))
                elif any(keyword in module_name for keyword in ['utils', 'rate_limiter', 'progress_tracker', 'platform_context']):
                    categories['Utility Modules'].append((module_name, module_sig))
                elif 'test' in module_name:
                    categories['Test Modules'].append((module_name, module_sig))
                elif 'scripts' in module_name:
                    categories['Script Modules'].append((module_name, module_sig))
                elif any(keyword in module_name for keyword in ['main', 'web_app', 'config', 'models', 'database', 'activitypub', 'ollama', 'image_processor', 'session_manager']):
                    categories['Core Modules'].append((module_name, module_sig))
                else:
                    categories['Other Modules'].append((module_name, module_sig))
            
            for category, modules in categories.items():
                if modules:
                    f.write(f"## {category}\n\n")
                    for module_name, module_sig in modules:
                        f.write(f"- [{module_name}]({module_name.replace('.', '_')}.md)")
                        if module_sig.docstring:
                            first_line = module_sig.docstring.split('\n')[0].strip()
                            f.write(f" - {first_line}")
                        f.write("\n")
                    f.write("\n")
    
    def _generate_module_documentation(self, module_sig: ModuleSignature, output_dir: Path) -> None:
        """Generate documentation for a single module"""
        filename = module_sig.name.replace('.', '_') + '.md'
        file_path = output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# {module_sig.name}\n\n")
            
            if module_sig.docstring:
                f.write(f"{module_sig.docstring}\n\n")
            
            f.write(f"**File Path:** `{module_sig.path}`\n\n")
            
            # Constants
            if module_sig.constants:
                f.write("## Constants\n\n")
                for constant in module_sig.constants:
                    f.write(f"- `{constant}`\n")
                f.write("\n")
            
            # Classes
            if module_sig.classes:
                f.write("## Classes\n\n")
                for class_sig in module_sig.classes:
                    self._write_class_documentation(f, class_sig)
            
            # Functions
            if module_sig.functions:
                f.write("## Functions\n\n")
                for func_sig in module_sig.functions:
                    self._write_function_documentation(f, func_sig)
    
    def _write_class_documentation(self, f, class_sig: ClassSignature) -> None:
        """Write documentation for a class"""
        f.write(f"### {class_sig.name}\n\n")
        
        # Class signature
        bases_str = f"({', '.join(class_sig.bases)})" if class_sig.bases else ""
        f.write(f"```python\nclass {class_sig.name}{bases_str}\n```\n\n")
        
        if class_sig.docstring:
            f.write(f"{class_sig.docstring}\n\n")
        
        # Decorators
        if class_sig.decorators:
            f.write("**Decorators:**\n")
            for decorator in class_sig.decorators:
                f.write(f"- `@{decorator}`\n")
            f.write("\n")
        
        # Class variables
        if class_sig.class_variables:
            f.write("**Class Variables:**\n")
            for var in class_sig.class_variables:
                f.write(f"- `{var}`\n")
            f.write("\n")
        
        # Properties
        if class_sig.properties:
            f.write("**Properties:**\n")
            for prop in class_sig.properties:
                f.write(f"- `{prop}`\n")
            f.write("\n")
        
        # Methods
        if class_sig.methods:
            f.write("**Methods:**\n\n")
            for method_sig in class_sig.methods:
                self._write_function_documentation(f, method_sig, is_method=True)
    
    def _write_function_documentation(self, f, func_sig: FunctionSignature, is_method: bool = False) -> None:
        """Write documentation for a function"""
        indent = "#### " if is_method else "### "
        f.write(f"{indent}{func_sig.name}\n\n")
        
        # Function signature
        async_prefix = "async " if func_sig.is_async else ""
        args_str = ", ".join(func_sig.args)
        return_str = f" -> {func_sig.return_annotation}" if func_sig.return_annotation else ""
        
        f.write(f"```python\n{async_prefix}def {func_sig.name}({args_str}){return_str}\n```\n\n")
        
        if func_sig.docstring:
            f.write(f"{func_sig.docstring}\n\n")
        
        # Decorators
        if func_sig.decorators:
            f.write("**Decorators:**\n")
            for decorator in func_sig.decorators:
                f.write(f"- `@{decorator}`\n")
            f.write("\n")
        
        # Method type
        if func_sig.is_classmethod:
            f.write("**Type:** Class method\n\n")
        elif func_sig.is_staticmethod:
            f.write("**Type:** Static method\n\n")
        elif func_sig.is_method:
            f.write("**Type:** Instance method\n\n")

def main():
    """Main function to generate API documentation"""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    generator = APIDocumentationGenerator(project_root)
    
    print("Scanning project for Python files...")
    generator.scan_project()
    
    print(f"Found {len(generator.modules)} modules")
    
    output_dir = Path(project_root) / 'docs' / 'api' / 'generated'
    print(f"Generating documentation in {output_dir}")
    
    generator.generate_markdown_documentation(output_dir)
    
    print("API documentation generation complete!")

if __name__ == '__main__':
    main()