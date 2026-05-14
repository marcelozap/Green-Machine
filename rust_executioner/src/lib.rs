use pyo3::prelude::*;

/// Cumulative sum used by the Python backtester equity loop (PyO3 wiring).
/// Replace inner loop with full executioner simulation as data paths land.
#[pyfunction]
fn cumulative_sum_py(values: Vec<f64>) -> Vec<f64> {
    let mut out = Vec::with_capacity(values.len());
    let mut s = 0.0_f64;
    for v in values {
        s += v;
        out.push(s);
    }
    out
}

#[pymodule]
fn execution_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cumulative_sum_py, m)?)?;
    Ok(())
}
