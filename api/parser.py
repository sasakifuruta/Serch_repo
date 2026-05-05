import ast


class PythonParser(ast.NodeVisitor):
    def __init__(self, code: str):
        self.code = code
        self.chunks = []
        self.current_class = None

    def visit_ClassDef(self, node: ast.ClassDef):
        # クラスチャンク
        self.chunks.append({
            "chunk_type": "class",
            "class_name": node.name,
            "content": ast.get_source_segment(self.code, node)
        })

        # 状態更新（クラス内に入る）
        prev_class = self.current_class
        self.current_class = node.name

        self.generic_visit(node)

        # 状態戻す
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        func_code = ast.get_source_segment(self.code, node)

        if self.current_class:
            # クラス内メソッド
            self.chunks.append({
                "chunk_type": "method",
                "class_name": self.current_class,
                "function_name": node.name,
                "content": func_code
            })
        else:
            # グローバル関数
            self.chunks.append({
                "chunk_type": "function",
                "function_name": node.name,
                "content": func_code
            })

        self.generic_visit(node)


def parse_python(code: str, tree):
    parser = PythonParser(code)
    parser.visit(tree)
    return parser.chunks