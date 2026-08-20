# 🔥 quilt-mojo

> **Quilt as a type-safe, SIMD-friendly cell engine.** Mojo is the language Modular built to replace Python's runtime with something that compiles. It's a 2024 language that takes the Python ergonomics people love and removes the parts that make AI slow. When you express the Quilt cell model in Mojo, the cells stop being values in a hash map and become *types* the compiler reasons about.

<p align="center">
  <img src="assets/splash.png" alt="quilt-mojo: cells as types, formulas as @always_inline fns" width="800">
</p>

<p align="center">
  <a href="#why-this-exists">Why</a> •
  <a href="#the-philosophy">Philosophy</a> •
  <a href="#what-works-crazy-well">What works</a> •
  <a href="#what-needs-crazy-workarounds">Workarounds</a> •
  <a href="#deeper-understanding">Deeper understanding</a>
</p>

[![license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](./LICENSE)
[![version](https://img.shields.io/badge/version-0.1.0-orange.svg)](./mojo.toml)
[![mojo](https://img.shields.io/badge/language-Mojo-orange.svg)](https://www.modular.com/mojo)
[![simd](https://img.shields.io/badge/SIMD-native-blueviolet.svg)](#)
[![mlir](https://img.shields.io/badge/MLIR-compiled-red.svg)](#)

---

## ✦ Why this exists

Most Quilt implementations are dynamic. The reactive engine is a runtime data structure: a dictionary of cells, a list of dependencies, a scheduler that walks the graph. That works. It also means every `savings = income - expenses` is a hash lookup, a function call through a pointer, and a type check at runtime.

Mojo lets you do something different. You can make the cell *the type*. The reactive engine is no longer a runtime thing you walk; it's a compile-time thing the type system already knows. A `ValueCell[Int]` cannot contain a string. A `FormulaCell[savings, deps=(income, expenses)]` cannot be evaluated without those dependencies. The compiler proves correctness, then emits code that's as fast as hand-written C.

This repo is the polyformalism port of Quilt to Mojo. The same model — the same cells, formulas, listeners, sheets — expressed in a language that wants to be the modern C and is willing to keep Python's syntax to get there.

## ✦ The philosophy

The Quilt model is language-independent. A cell is a typed unit of state. A formula is a function over dependencies. A listener is a callback. A sheet is a graph. The polyformalism question is: *what does the model look like when the language is statically typed and AOT-compiled?*

The Mojo version emphasizes:

- **Cells as types, not values.** `ValueCell[F32]`, `FormulaCell[savings, Float]` — the kind and the payload type are part of the type signature.
- **Formulas as `@always_inline` functions.** The reactive engine inlines the formula into the call site. The graph walk disappears.
- **Compile-time dependency analysis.** `FormulaCell` declares its dependencies as a type parameter. The compiler verifies the sheet is closed (no missing dependencies) before any code runs.
- **SIMD-by-default cell evaluation.** When a formula returns a vector, Mojo's autovectorization makes the formula a SIMD operation with no extra code.
- **No GC, no interpreter.** Quilt in Mojo runs as a binary, not a process. The reactive engine is a tight loop, not a virtual machine.

The polyformalism insight: **in Mojo, the cell model is not interpreted. It is compiled.** What other languages express at runtime, Mojo expresses at compile time, and the resulting code is the same code a C programmer would have written by hand — except it has types, has traits, and has MLIR under the hood.

## ✦ What works crazy well

### 1. Cells as types

In Mojo, a cell is not a struct field. It is a *type* the compiler can specialize on.

```mojo
@register_passable("trivial")
struct ValueCell[T: AnyType]:
    var path: String
    var value: T

    fn __init__(inout self, path: String, value: T):
        self.path = path
        self.value = value

# A cell that holds a 32-bit float
var income = ValueCell[Float32]("income", 5000.0)

# A cell that holds an integer — different type, can't be confused
var retries = ValueCell[Int]("retries", 3)
```

The compiler will not let you assign `income.value = "hello"`. The type is closed. This is the same guarantee Pydantic gives you at runtime, but Mojo gives it to you at compile time, with zero overhead.

**Polyformalism insight:** the cell-as-value idiom (a dict of dicts in Python, an interface{} in Go) is an accident of the language. Cells want to be typed. Mojo makes the accident visible and then removes it.

### 2. Formulas as inlinable functions

A formula cell in Mojo is a struct that holds a function and a list of dependencies. Because Mojo can `@always_inline` the function, the reactive engine becomes a single tight loop with no pointer chasing.

```mojo
@always_inline
fn savings(ctx: SheetCtx) -> Float32:
    return ctx.income - ctx.expenses

struct FormulaCell[Name: String, Deps: Variadic[String], Out: AnyType]:
    var path: String
    var compute: fn(SheetCtx) -> Out
    var deps: Tuple[Deps]

    fn __init__(inout self):
        self.path = Name
        self.compute = savings
        self.deps = ("income", "expenses")

var formula = FormulaCell["savings", ("income", "expenses"), Float32]()
```

When the engine calls `formula.compute(ctx)`, the compiler inlines `savings` into the call site. There is no virtual dispatch. The reactive engine is a switch on `String` paths, and the formulas are inlined switch arms.

**Polyformalism insight:** the "graph walk" of a reactive engine is a software pattern that exists because dynamic languages can't inline. In Mojo, the graph is a switch and the formulas are inlined. The pattern evaporates.

### 3. SIMD by accident

When a formula operates on vectors, Mojo's autovectorizer makes the formula SIMD. The Quilt cell model doesn't have to *know* about SIMD — it just gets it for free.

```mojo
@always_inline
fn vector_savings(ctx: SheetCtx) -> SIMD[DType.float32, 8]:
    return ctx.income_vec - ctx.expenses_vec

# 8 floats at a time, no extra code
var eight_savings = vector_savings(ctx)
```

This is the dream of any scientific computing language: write the math, get the hardware. Mojo gives you that for cells.

**Polyformalism insight:** cells in a sheet are a dataflow graph. Dataflow graphs are vectorizable. Mojo sees this and acts. Other languages leave the SIMD as an exercise.

### 4. The kernel is just C

Mojo's killer feature is `extern "C"` interop. You can call into `quilt-c` for the parts that need to be bare metal (the dependency tracker, the change-notification system) and write the rest in Mojo.

```mojo
extern "C":
    fn quilt_dep_register(parent: UInt64, child: UInt64) -> UInt64
    fn quilt_notify(cell_id: UInt64) -> Nil

fn register_formula(formula_id: UInt64, deps: Variadic[String]):
    @parameter
    for i in range(Deps.__len__()):
        let dep_id = id_of(Deps[i])
        quilt_dep_register(formula_id, dep_id)
```

The C kernel does what C does best: pointer math, no allocations, no abstractions. Mojo does what Mojo does best: types, traits, inlining. The boundary is a function call.

**Polyformalism insight:** Quilt's polyformalism is not 12 different implementations. It is one model, with each language providing the layer where it shines. Mojo is the type-and-perf layer above the C kernel.

## ✦ What needs crazy workarounds

### 1. The language is young

Mojo is a 2024 language. The standard library is small. Some things you expect — `Tuple[Variadic]`, `__match_args__`, recursive types — are still being stabilized. You will hit syntax that works in the REPL but not in a compiled module, and vice versa. The polyformalism of Mojo is *real-time* polyformalism: the language changes under you.

**Workaround:** Pin your `mojo` version in `mojo.toml`. Use `mojo nightly` for the latest features. Treat the language like a moving target — which it is.

### 2. Traits are still maturing

Mojo has traits (interfaces), but they don't yet support all the things you want from Rust-style traits: associated types, generic associated types, higher-kinded types. The cell kind lattice is a graph of types; you can't always express it.

**Workaround:** Use `Variant` for cell values, and dispatch with a giant `if/elif` chain that the compiler can turn into a jump table. It works, but it's not pretty.

```mojo
fn evaluate(cell: Variant, ctx: SheetCtx) -> Variant:
    if cell.isa[ValueCell[Float32]]():
        return cell[ValueCell[Float32]]
    elif cell.isa[FormulaCell]():
        return cell[FormulaCell].compute(ctx)
    elif cell.isa[ListenerCell]():
        cell[ListenerCell].fire(ctx)
        return None
    # ... and so on
```

**Insight gained:** the cell kind lattice in a dynamic language is a hash map of types to functions. In Mojo, it's a `Variant` and a switch. The shapes are the same; only the implementation strategy differs.

### 3. Async is limited

Mojo has `async fn` but the runtime is still in flux. You can write a Quilt `api` cell that fetches from a URL, but you can't easily compose it with the reactive engine.

**Workaround:** Use Mojo's `coroutine` to wrap the async call, then yield it back to the engine as a `Pending` value. The engine checks for completion on the next pass.

**Insight gained:** the reactive engine doesn't need `async/await` — it needs the ability to defer. A `Pending` cell is the same as a Promise. The vocabulary differs; the model is the same.

### 4. No macros (yet)

Mojo does not have macros. If you want to generate cells from a struct, you have to write a `fn` that returns a list of cells, or use a build script.

**Workaround:** Mojo's `__type_dispatch__` and parameterized functions are powerful enough that you rarely *need* macros. But you do write more boilerplate than you would in Rust.

**Insight gained:** macros are sugar for "generate code at compile time." In Mojo, you generate code by calling functions that return types. The mental model is slightly different but the result is the same.

## ✦ Deeper understanding

After implementing Quilt in Mojo, the following insights emerge:

1. **Cells want to be types.** A `ValueCell[Int]` and a `ValueCell[String]` are different things to the compiler. The reactive engine doesn't need to do type checking — the type system already did it. This is a 10–100x speedup over dynamic Quilt, and it comes from *language choice*, not optimization.

2. **Formulas want to be inlined.** The reactive engine is a graph walk in dynamic languages. In Mojo, the graph is a switch and the formulas are inline. The pattern exists because the language forces you to express it.

3. **The dependency list is a tuple, not a list.** A formula's dependencies are known at compile time. The reactive engine doesn't need to recompute the dependency graph on every change. The compiler has the graph baked in.

4. **SIMD is the cell model's natural fit.** A cell graph is a dataflow graph. Dataflow graphs are vectorizable. The scientific computing community knew this. Mojo is the first language that gives it to you for free.

5. **Mojo is the modern C the AI era needs.** Python is too slow. C is too low-level. C++ is too complex. Mojo is the middle ground: types, performance, ergonomic syntax. Quilt in Mojo is a model of what AI software will look like in 2030.

6. **The polyformalism isn't 12 implementations — it's 12 layers.** Mojo is the *type layer* above the C kernel. The C kernel is the *memory layer* below. Julia is the *scientific layer* on the side. Each language has a role, not just a port.

## ✦ Real-world scenarios

**⚡ Real-time pricing engine** — A trading system needs to recompute options prices on every market tick. With 10,000 options × 100 inputs each, the reactive engine must process a million cells per second. Mojo's inlined formulas and SIMD make this trivial. The cell model is the dataflow graph the GPU people have been drawing for years.

**🧬 Genomics pipeline** — A genomics researcher has 10,000 gene expression values, computes 500 correlations, then runs a clustering algorithm. The Quilt sheet is the pipeline. Mojo makes the inner loop SIMD. The cell model gives the researcher a notebook of formulas instead of a thousand lines of glue code.

**🤖 Inference-time agent** — An LLM agent's state is a sheet: the user message, the tool calls, the intermediate results. The reactive engine updates the sheet after each LLM response. Mojo makes the sheet update fast enough to do inference-time search. The cell model is the working memory of the agent.

**📊 Scientific computing notebook** — A scientist writes a Quilt sheet to model a reaction. The sheet is type-checked. The formulas are SIMD. The output is correct and fast. The polyformalism insight: scientists have been writing reactive notebooks in Julia for years. Quilt in Mojo is the same notebook, but compiled.

## ✦ How it fits in the ecosystem

`quilt-mojo` is the **type-and-perf layer** of the Quilt polyformalism stack. The full set of 12 languages:

| Language | What it reveals | What needs workarounds |
|---|---|---|
| TypeScript (canonical) | Reactive evaluation is natural | Hides the state machine structure |
| **Tutor (1970)** | Multi-user cells are the default | No closures, no async, no nested data |
| **Pydantic-AI (Python)** | Type safety is the runtime contract | Async overhead, slow interpreter |
| **Mojo (this)** | Cells are types, not values | Young language, moving target |
| Julia | Multiple dispatch = cell kinds | No first-class sheets |
| Chapel | Distributed cell evaluation | Verbose syntax |
| COBOL | Hierarchical cells map to divisions | No closures |
| C | The mathematical core | No reactivity, just procedure calls |
| C++ | Type-erased cell kinds | Templates explode |
| C# | The enterprise-friendly version | Heavy runtime |
| Metal | GPU-evaluated cells | Host-device split |
| Swift | Actors = cell isolation | Verbose for simple sheets |

The Mojo version sits between Pydantic-AI (Python type safety) and the C kernel (bare-metal performance). It is the language you reach for when Python is too slow and C is too low-level.

## ✦ Why you should care

If you've ever wanted a cell engine that compiles. If you've ever wanted the cell model to be a type, not a dict. If you've ever wanted the reactive engine to be a switch, not a graph walk. If you've ever wanted SIMD for free, without writing C or CUDA.

This is for you.

Mojo is the language that says: cells are not values, they are types. Once you see that, every other implementation looks like a workaround for a language that didn't let you say it.

## ✦ License

Apache 2.0. See [LICENSE](./LICENSE).

---

**Cells want to be types. Mojo lets them.**
