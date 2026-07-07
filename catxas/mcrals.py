# -*- coding: utf-8 -*-
"""
Created on Thu Jul  2 10:20:28 2026

@author: ashoff
"""

import os 

import numpy as np
import pandas as pd

import time

from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

from pymcr.mcr import McrAR
from pymcr.regressors import NNLS, OLS
from pymcr.constraints import ConstraintNonneg, ConstraintNorm, Constraint

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

import ipywidgets as widgets
from IPython.display import display


def get_unique_spectra_kmeans(df, n_components):
    """
    Find n most unique spectra using k-means clustering.
    
    Performs k-means clustering on the spectra and returns the spectrum
    closest to each cluster center.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Spectral data with rows = energy points, columns = spectra
    n_components : int
        Number of unique spectra/components to find
        
    Returns:
    --------
    pandas.DataFrame
        Subset of df containing the n most representative spectra
    dict
        Dictionary with 'column_indices' (list of selected column indices)
        and 'column_names' (list of selected column names)
    """
    # Transpose so each spectrum is a row
    X = df.T.values
    
    # Perform k-means clustering
    kmeans = KMeans(n_clusters=n_components, random_state=42, n_init=10)
    kmeans.fit(X)
    
    # Find spectra closest to each cluster center
    unique_indices = []
    for center in kmeans.cluster_centers_:
        distances = np.linalg.norm(X - center, axis=1)
        unique_indices.append(np.argmin(distances))
    
    # Get column names
    column_names = [df.columns[i] for i in unique_indices]
    
    # Return the unique spectra and metadata
    return df.iloc[:, unique_indices], {
        'column_indices': unique_indices,
        'column_names': column_names
    }


def get_unique_spectra_pca(df, n_components):
    """
    Find spectra with extreme principal component scores.
    
    Performs PCA and selects spectra that have the maximum absolute score
    for each principal component.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Spectral data with rows = energy points, columns = spectra
    n_components : int
        Number of unique spectra/components to find
        
    Returns:
    --------
    pandas.DataFrame
        Subset of df containing the n spectra with extreme PC scores
    dict
        Dictionary with 'column_indices' (list of selected column indices)
        and 'column_names' (list of selected column names)
    """
    X = df.T.values
    
    pca = PCA(n_components=n_components)
    scores = pca.fit_transform(X)
    
    unique_indices = []
    for i in range(n_components):
        # Get spectrum with max absolute score for each PC
        idx = np.argmax(np.abs(scores[:, i]))
        if idx not in unique_indices:
            unique_indices.append(idx)
    
    # If we need more spectra, add those with next highest scores
    while len(unique_indices) < n_components:
        remaining_scores = np.delete(np.abs(scores).max(axis=1), unique_indices)
        remaining_idx = np.delete(np.arange(len(X)), unique_indices)
        idx = remaining_idx[np.argmax(remaining_scores)]
        unique_indices.append(idx)
    
    # Get column names
    column_names = [df.columns[i] for i in unique_indices[:n_components]]
    
    return df.iloc[:, unique_indices[:n_components]], {
        'column_indices': unique_indices[:n_components],
        'column_names': column_names
    }


def get_unique_spectra_dissimilarity(df, n_components):
    """
    Greedy selection of most dissimilar spectra.
    
    Starts with the spectrum with highest variance, then iteratively adds
    the spectrum that is most dissimilar to already selected spectra.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Spectral data with rows = energy points, columns = spectra
    n_components : int
        Number of unique spectra/components to find
        
    Returns:
    --------
    pandas.DataFrame
        Subset of df containing the n most dissimilar spectra
    dict
        Dictionary with 'column_indices' (list of selected column indices)
        and 'column_names' (list of selected column names)
    """
    X = df.T.values
    
    # Start with the spectrum with highest variance
    variances = np.var(X, axis=1)
    selected_indices = [np.argmax(variances)]
    
    # Iteratively add most dissimilar spectrum
    while len(selected_indices) < n_components:
        # Calculate minimum similarity to already selected spectra
        similarities = cosine_similarity(X, X[selected_indices])
        max_similarities = similarities.max(axis=1)
        
        # Exclude already selected
        max_similarities[selected_indices] = np.inf
        
        # Add spectrum with minimum similarity (maximum dissimilarity)
        selected_indices.append(np.argmin(max_similarities))
    
    # Get column names
    column_names = [df.columns[i] for i in selected_indices]
    
    return df.iloc[:, selected_indices], {
        'column_indices': selected_indices,
        'column_names': column_names
    }


def get_unique_spectra_simplisma(df, n_components):
    """
    SIMPLISMA algorithm for pure variable detection.
    
    Simple-to-use Interactive Self-modeling Mixture Analysis identifies
    pure variables (energy points) with characteristic features, then
    selects spectra that maximize intensity at those points.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Spectral data with rows = energy points, columns = spectra
    n_components : int
        Number of unique spectra/components to find
        
    Returns:
    --------
    pandas.DataFrame
        Subset of df containing n spectra selected via SIMPLISMA
    dict
        Dictionary with 'column_indices' (list of selected column indices)
        and 'column_names' (list of selected column names)
    """
    X = df.values  # energy points × spectra
    n_vars, n_spectra = X.shape
    
    # Calculate purity spectrum
    mean_spectrum = X.mean(axis=1, keepdims=True)
    std_spectrum = X.std(axis=1, keepdims=True)
    
    # Avoid division by zero
    std_spectrum[std_spectrum == 0] = 1e-10
    
    purity = std_spectrum.flatten() / (mean_spectrum.flatten() + 1e-10)
    
    selected_indices = []
    
    for _ in range(n_components):
        if len(selected_indices) == 0:
            # First pure variable
            pure_var_idx = np.argmax(purity)
        else:
            # Calculate corrected purity
            # (orthogonalize with respect to already selected)
            weights = X[selected_indices, :].T
            proj = np.linalg.lstsq(weights, X.T, rcond=None)[0]
            residuals = X.T - weights @ proj
            
            purity_corrected = residuals.std(axis=0) / (residuals.mean(axis=0) + 1e-10)
            pure_var_idx = np.argmax(np.abs(purity_corrected))
        
        selected_indices.append(pure_var_idx)
    
    # Return spectra with max intensity at those energy points
    unique_spec_indices = []
    for var_idx in selected_indices:
        spec_idx = np.argmax(X[var_idx, :])
        unique_spec_indices.append(spec_idx)
    
    # Get column names
    column_names = [df.columns[i] for i in unique_spec_indices]
    
    return df.iloc[:, unique_spec_indices], {
        'column_indices': unique_spec_indices,
        'column_names': column_names
    }


def calculate_diversity(spectra_df):
    """
    Calculate diversity score for selected spectra.
    
    Higher score indicates more diverse/unique spectra based on
    pairwise cosine similarity.
    
    Parameters:
    -----------
    spectra_df : pandas.DataFrame
        Selected spectra to evaluate
        
    Returns:
    --------
    float
        Diversity score (0 to 1, higher = more diverse)
    """
    X = spectra_df.T.values
    
    # Calculate pairwise cosine similarities
    similarities = cosine_similarity(X)
    
    # Exclude diagonal (self-similarity)
    n = similarities.shape[0]
    mask = ~np.eye(n, dtype=bool)
    off_diagonal_similarities = similarities[mask]
    
    # Diversity = 1 - mean similarity
    diversity = 1 - np.mean(off_diagonal_similarities)
    
    return diversity


def compare_all_methods(df, n_components, mcr_als_function=None):
    """
    Run all seed selection methods and compare results.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Spectral data with rows = energy points, columns = spectra (time series)
    n_components : int
        Number of components/unique spectra to find
    mcr_als_function : callable, optional
        Your MCR-ALS function that takes (df, initial_spectra) and returns results
        
    Returns:
    --------
    dict
        Results from all methods containing:
        - 'initial_spectra': DataFrame of selected spectra
        - 'column_indices': List of selected column indices
        - 'column_names': List of selected column names
        - 'init_time': Time for seed selection (seconds)
        - 'diversity_score': Diversity metric
        - Additional MCR-ALS results if function provided
    """
    
    methods = {
        'PCA': get_unique_spectra_pca,
        'K-Means': get_unique_spectra_kmeans,
        'Dissimilarity': get_unique_spectra_dissimilarity,
        'SIMPLISMA': get_unique_spectra_simplisma
    }
    
    results = {}
    
    print("="*70)
    print(f"Comparing seed selection methods for {n_components} components")
    print(f"Dataset: {df.shape[0]} energy points × {df.shape[1]} spectra")
    print("="*70)
    
    for method_name, method_func in methods.items():
        print(f"\n{method_name}:")
        print("-" * 40)
        
        # Time the initialization
        start = time.time()
        try:
            initial_spectra, metadata = method_func(df, n_components)
            init_time = time.time() - start
            
            # Calculate diversity metrics
            diversity_score = calculate_diversity(initial_spectra)
            
            results[method_name] = {
                'initial_spectra': initial_spectra,
                'column_indices': metadata['column_indices'],
                'column_names': metadata['column_names'],
                'init_time': init_time,
                'diversity_score': diversity_score,
                'status': 'success'
            }
            
            print(f"  ✓ Initialization time: {init_time:.4f} s")
            print(f"  ✓ Selected columns: {metadata['column_names']}")
            print(f"  ✓ Diversity score: {diversity_score:.4f}")
            
            # Run MCR-ALS if function provided
            if mcr_als_function is not None:
                mcr_start = time.time()
                mcr_result = mcr_als_function(df, initial_spectra)
                mcr_time = time.time() - mcr_start
                
                results[method_name]['mcr_result'] = mcr_result
                results[method_name]['mcr_time'] = mcr_time
                results[method_name]['total_time'] = init_time + mcr_time
                
                # Extract quality metrics (adjust based on your MCR-ALS output)
                if hasattr(mcr_result, 'r2'):
                    results[method_name]['r2'] = mcr_result.r2
                    print(f"  ✓ MCR-ALS R²: {mcr_result.r2:.4f}")
                
                print(f"  ✓ MCR-ALS time: {mcr_time:.4f} s")
                print(f"  ✓ Total time: {init_time + mcr_time:.4f} s")
                
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            results[method_name] = {'status': 'failed', 'error': str(e)}
    
    print("\n" + "="*70)
    print_summary(results, mcr_als_function is not None)
    
    return results


def print_summary(results, has_mcr=False):
    """
    Print summary comparison table.
    
    Parameters:
    -----------
    results : dict
        Results from compare_all_methods()
    has_mcr : bool
        Whether MCR-ALS was run
    """
    print("\nSUMMARY:")
    print("-" * 70)
    
    # Sort by initialization time
    successful_results = {k: v for k, v in results.items() if v['status'] == 'success'}
    
    if has_mcr:
        print(f"{'Method':<20} {'Init(s)':<10} {'MCR(s)':<10} {'Total(s)':<10} {'Diversity':<12} {'R²':<8}")
        print("-" * 70)
        for method_name in sorted(successful_results.keys(), 
                                 key=lambda x: successful_results[x]['total_time']):
            r = successful_results[method_name]
            r2_str = f"{r.get('r2', 0):.4f}" if 'r2' in r else "N/A"
            print(f"{method_name:<20} {r['init_time']:<10.4f} {r['mcr_time']:<10.4f} "
                  f"{r['total_time']:<10.4f} {r['diversity_score']:<12.4f} {r2_str:<8}")
    else:
        print(f"{'Method':<20} {'Time(s)':<10} {'Diversity':<12}")
        print("-" * 70)
        for method_name in sorted(successful_results.keys(), 
                                 key=lambda x: successful_results[x]['init_time']):
            r = successful_results[method_name]
            print(f"{method_name:<20} {r['init_time']:<10.4f} {r['diversity_score']:<12.4f}")


def visualize_comparison(df, results):
    """
    Create visualization comparing initial spectra from all methods.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Original spectral data
    results : dict
        Results from compare_all_methods()
        
    Returns:
    --------
    matplotlib.figure.Figure
        Figure with subplots showing selected spectra from each method
    """
    n_methods = len([r for r in results.values() if r['status'] == 'success'])
    
    fig, axes = plt.subplots(n_methods, 1, figsize=(12, 4*n_methods))
    if n_methods == 1:
        axes = [axes]
    
    for idx, (method_name, result) in enumerate(results.items()):
        if result['status'] != 'success':
            continue
            
        ax = axes[idx]
        initial_spectra = result['initial_spectra']
        
        # Plot each initial spectrum
        for i, col in enumerate(initial_spectra.columns):
            ax.plot(initial_spectra.index, initial_spectra[col], 
                   label=f'Spectrum {col}', linewidth=2)
        
        ax.set_xlabel('Energy (eV)', fontweight='bold')
        ax.set_ylabel('Intensity', fontweight='bold')
        ax.set_title(f'{method_name} - Initial Spectra (Time: {result["init_time"]:.4f}s, '
                    f'Diversity: {result["diversity_score"]:.4f})', fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def run_complete_comparison(df, n_components, mcr_als_function=None):
    """
    One-stop function to run complete seed selection comparison.
    
    Compares all seed selection methods, optionally runs MCR-ALS with each,
    and visualizes the selected initial spectra.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Spectral data with rows = energy points, columns = spectra (time series)
    n_components : int
        Number of components/unique spectra to find
    mcr_als_function : callable, optional
        Your MCR-ALS function that takes (df, initial_spectra) and returns results
        
    Returns:
    --------
    results : dict
        Dictionary of results from all methods containing selected column
        indices, names, timing, diversity scores, and optionally MCR-ALS results
    fig : matplotlib.figure.Figure
        Visualization of selected spectra from each method
    """
    # Run comparison
    results = compare_all_methods(df, n_components, mcr_als_function)
    
    # Visualize
    fig = visualize_comparison(df, results)
    
    return results, fig


class ConstraintZeroByIndex(Constraint):
    """
    Custom constraint to force specific components to zero at specified indices.
    
    This constraint is useful for MCR-ALS when you know certain components
    should not contribute at specific spectral points (e.g., energy values or
    time points where a component is known to be absent).
    
    Parameters:
    -----------
    zero_dict : dict
        Dictionary mapping component indices to spectral indices where that
        component should be constrained to zero.
        
        Format: {component_index: indices}
        
        - component_index (int): The component number (0-indexed)
        - indices: Can be:
            * Single index (int): e.g., 5
            * List of indices: e.g., [5, 10, 15]
            * Range object: e.g., range(10, 20)
            * List of ranges/indices: e.g., [range(0, 10), range(50, 60), 25]
    
    Examples:
    ---------
    # Force component 0 to be zero at indices 55-56
    zero_dict = {0: range(55, 57)}
    constraint = ConstraintZeroByIndex(zero_dict)
    
    # Force component 1 to be zero at specific indices
    zero_dict = {1: [0, 5, 10]}
    constraint = ConstraintZeroByIndex(zero_dict)
    
    # Force multiple components with different regions
    zero_dict = {
        0: range(55, 57),      # Component 0 zero at indices 55-56
        2: [0, 1, 2],          # Component 2 zero at indices 0-2
        4: [range(0, 10), 50]  # Component 4 zero at 0-9 and at 50
    }
    constraint = ConstraintZeroByIndex(zero_dict)
    
    # No constraints (empty dict)
    zero_dict = {}
    constraint = ConstraintZeroByIndex(zero_dict)
    
    Usage with MCR-ALS:
    -------------------
    from pymcr.mcr import McrAR
    from pymcr.constraints import ConstraintNonneg, ConstraintNorm
    from mcr_constraints import ConstraintZeroByIndex
    
    # Define zero constraints
    zero_dict = {
        0: range(100, 150),  # Component 0 = 0 at spectra 100-149
        1: [0, 1, 2]         # Component 1 = 0 at spectra 0-2
    }
    zero_constraint = ConstraintZeroByIndex(zero_dict)
    
    # Set up MCR with constraints
    c_constraints = [ConstraintNonneg(), ConstraintNorm(), zero_constraint]
    st_constraints = [ConstraintNonneg(), ConstraintNorm()]
    
    mcrar = McrAR(c_constraints=c_constraints, st_constraints=st_constraints)
    mcrar.fit(D, ST=initial_spectra)
    
    Notes:
    ------
    - Works with concentration (C) matrix constraints in MCR-ALS
    - Indices refer to rows in the C matrix (typically spectra/time points)
    - Component indices are 0-based (first component = 0)
    - Returns a copy of C with specified values set to zero
    """
    
    def __init__(self, zero_dict):
        """
        Initialize the zero constraint.
        
        Parameters:
        -----------
        zero_dict : dict
            Dictionary defining which components should be zero at which indices
        """
        self.zero_dict = zero_dict
        
    def transform(self, C):
        """
        Apply zero constraints to the concentration matrix.
        
        Parameters:
        -----------
        C : numpy.ndarray
            Concentration matrix (spectra × components)
            
        Returns:
        --------
        numpy.ndarray
            Modified concentration matrix with zeros applied
        """
        C_new = C.copy()
        
        for comp, regions in self.zero_dict.items():
            # Collect all row indices for this component
            rows = []
            
            # Handle different input formats
            regions_list = regions if isinstance(regions, (list, tuple)) else [regions]
            
            for r in regions_list:
                if isinstance(r, range):
                    # Convert range to list
                    rows.extend(list(r))
                elif np.isscalar(r):
                    # Single index
                    rows.append(r)
                else:
                    # Array-like (list, numpy array, etc.)
                    rows.extend(list(r))
            
            # Apply zero constraint
            C_new[np.array(rows), comp] = 0
            
        return C_new


def run_mcr_als(df_data, initial_spectra_indices,
                c_constraints=None, st_constraints=None,
                fast_solve=True, max_iter=5000,
                tol_increase=50000, tol_n_increase=100000,
                tol_err_change=1e-9, tol_n_above_min=100000,
                perturb_initial=True, perturbation_amount=0.01,
                verbose=True):
    """
    Run MCR-ALS analysis on spectral data.
    
    Parameters:
    -----------
    df_data : pandas.DataFrame
        Spectral data with rows = energy points, columns = spectra (time series)
    initial_spectra_indices : list of int
        List of spectrum indices to use as initial guesses (1-based indexing)
        The number of components is determined by the length of this list.
        Example: [1, 15, 30] selects 1st, 15th, and 30th spectra (3 components)
    c_constraints : list, optional
        Constraints for concentration matrix C
        Default: [ConstraintNonneg(), ConstraintNorm()]
    st_constraints : list, optional
        Constraints for spectra matrix ST
        Default: [ConstraintNonneg(), ConstraintNorm()]
    fast_solve : bool, optional
        If True, use OLS regression (fast). If False, use NNLS (slow but enforces non-negativity)
        Default: True
    max_iter : int, optional
        Maximum number of iterations (default: 5000)
    tol_increase : float, optional
        Tolerance for increase in error (default: 50000)
    tol_n_increase : int, optional
        Number of iterations to allow error increase (default: 100000)
    tol_err_change : float, optional
        Tolerance for change in error for convergence (default: 1e-9)
    tol_n_above_min : int, optional
        Number of iterations above minimum error before stopping (default: 100000)
    perturb_initial : bool, optional
        Whether to add small random noise to initial spectra to avoid lock-in at
        initial guess indices. Recommended to prevent concentrations going to zero
        at initial guess spectra. (default: True)
    perturbation_amount : float, optional
        Fraction of each point's value to use for perturbation noise (default: 0.01 = 1%)
        Each energy point is perturbed by ±perturbation_amount × value at that point
        Example: if perturbation_amount=0.01 and intensity=100, noise is ~±1
        Only used if perturb_initial=True
    verbose : bool, optional
        Print progress information (default: True)
    
    Returns:
    --------
    dict
        Dictionary containing:
        - 'C': Concentration matrix (n_spectra × n_components)
        - 'ST': Resolved spectra matrix (n_components × n_energy)
        - 'R': Residuals matrix (n_spectra × n_energy)
        - 'D': Original data matrix (n_spectra × n_energy)
        - 'D_reconstructed': Reconstructed data (C @ ST)
        - 'model': The fitted McrAR object
        - 'n_iter': Number of iterations performed
        - 'err': Final error value
        - 'converged': Whether algorithm converged
        - 'energy': Energy values from dataframe index
        - 'n_components': Number of components (derived from initial_spectra_indices)
    
    Examples:
    ---------
    # Basic usage with 1-based indexing and perturbation (recommended)
    results = run_mcr_als(
        df_data=df_spectra,
        initial_spectra_indices=[1, 15, 30]  # 3 components
    )
    
    # Without perturbation (if you have very clean initial guesses)
    results = run_mcr_als(
        df_data=df_spectra,
        initial_spectra_indices=[1, 15, 30],
        perturb_initial=False
    )
    
    # With larger perturbation for noisy data
    results = run_mcr_als(
        df_data=df_spectra,
        initial_spectra_indices=[1, 15, 30],
        perturb_initial=True,
        perturbation_amount=0.05  # 5% noise
    )
    
    # Access results
    C = results['C']  # Concentrations
    ST = results['ST']  # Resolved spectra
    R = results['R']  # Residuals
    
    # With custom constraints
    from mcr_constraints import ConstraintZeroByIndex
    
    zero_dict = {0: range(55, 57)}
    zero_constraint = ConstraintZeroByIndex(zero_dict)
    
    c_constraints = [ConstraintNonneg(), ConstraintNorm(), zero_constraint]
    st_constraints = [ConstraintNonneg(), ConstraintNorm()]
    
    results = run_mcr_als(
        df_data=df_spectra,
        initial_spectra_indices=[1, 15, 30, 45],  # 4 components
        c_constraints=c_constraints,
        st_constraints=st_constraints,
        fast_solve=True,
        max_iter=10000
    )
    
    # Use with seed selection methods
    from mcr_seed_selection import compare_all_methods
    
    seed_results = compare_all_methods(df_spectra, n_components=3)
    # Convert 0-based to 1-based
    pca_indices = [i + 1 for i in seed_results['PCA']['column_indices']]
    
    results = run_mcr_als(
        df_data=df_spectra,
        initial_spectra_indices=pca_indices
    )
    
    Notes:
    ------
    - Initial spectra perturbation helps avoid "lock-in" where concentrations
      go to zero except at initial guess indices
    - For best results, use diverse initial guesses from seed selection methods
    - Convergence is not always guaranteed; adjust tolerances if needed
    """
    
    # Determine number of components from initial_spectra_indices
    n_components = len(initial_spectra_indices)
    
    # Set default constraints if not provided
    if c_constraints is None:
        c_constraints = [ConstraintNonneg(), ConstraintNorm()]
    if st_constraints is None:
        st_constraints = [ConstraintNonneg(), ConstraintNorm()]
    
    # Extract data
    energy = df_data.index.values
    spectra_data = df_data.values
    
    # Transpose: D should be (n_spectra × n_energy)
    D = spectra_data.T
    
    if verbose:
        print("="*70)
        print("MCR-ALS Analysis")
        print("="*70)
        print(f"Data shape: {D.shape} (spectra × energy points)")
        print(f"Number of components: {n_components} (from {len(initial_spectra_indices)} initial spectra)")
        print(f"Solver: {'OLS (fast)' if fast_solve else 'NNLS (slow)'}")
        print(f"Max iterations: {max_iter}")
        print(f"Initial spectra indices (1-based): {initial_spectra_indices}")
    
    # Validate initial spectra indices
    if n_components == 0:
        raise ValueError("initial_spectra_indices cannot be empty")
    
    # Check indices are valid (1-based indexing)
    n_spectra = D.shape[0]
    for idx in initial_spectra_indices:
        if idx < 1 or idx > n_spectra:
            raise ValueError(f"Initial spectrum index {idx} is out of range "
                           f"(must be between 1 and {n_spectra})")
    
    # Build initial spectra array using 1-based indices
    initial_spectra = np.zeros([n_components, D.shape[1]])
    for i, index in enumerate(initial_spectra_indices):
        initial_spectra[i, :] = D[index - 1, :]  # Convert to 0-based for array indexing
    
    # Perturb initial spectra to avoid lock-in
    if perturb_initial:
    # Add random noise as a percentage of each point's value
        for i in range(n_components):
            # Generate random perturbation: each point ± perturbation_amount% of its value
            noise = np.random.randn(initial_spectra.shape[1]) * perturbation_amount * initial_spectra[i, :]
            initial_spectra[i, :] += noise
            # Ensure non-negative after perturbation
            initial_spectra[i, :] = np.maximum(initial_spectra[i, :], 0)
        
        if verbose:
            print(f"Initial spectra perturbed: ±{perturbation_amount*100}% at each energy point")
        
    if verbose:
        print(f"Initial spectra shape: {initial_spectra.shape}")
        print("-"*70)
    
    # Initialize MCR-ALS model
    if fast_solve:
        mcrar = McrAR(
            st_regr=OLS(), 
            c_regr=OLS(),
            max_iter=max_iter,
            c_constraints=c_constraints,
            st_constraints=st_constraints,
            tol_increase=tol_increase,
            tol_n_increase=tol_n_increase,
            tol_err_change=tol_err_change,
            tol_n_above_min=tol_n_above_min
        )
    else:
        mcrar = McrAR(
            st_regr=NNLS(),
            c_regr=NNLS(),
            max_iter=max_iter,
            c_constraints=c_constraints,
            st_constraints=st_constraints,
            tol_increase=tol_increase,
            tol_n_increase=tol_n_increase,
            tol_err_change=tol_err_change,
            tol_n_above_min=tol_n_above_min
        )
    
    # Run MCR-ALS
    if verbose:
        print("Running MCR-ALS...")
    
    mcrar.fit(D, ST=initial_spectra)
    
    # Extract results
    C = mcrar.C_  # Concentrations (n_spectra × n_components)
    ST = mcrar.ST_  # Spectra (n_components × n_energy)
    
    # Calculate reconstructed data and residuals
    D_reconstructed = C @ ST
    R = D - D_reconstructed
    
    # Get convergence information
    n_iter = mcrar.n_iter_opt
    final_err = mcrar.err[-1] if len(mcrar.err) > 0 else None
    converged = n_iter < max_iter
    
    if verbose:
        print("-"*70)
        print("Results:")
        print(f"  Iterations: {n_iter}/{max_iter}")
        print(f"  Converged: {converged}")
        print(f"  Final error: {final_err:.6e}" if final_err is not None else "  Final error: N/A")
        print(f"  Concentration matrix shape: {C.shape}")
        print(f"  Spectra matrix shape: {ST.shape}")
        print(f"  Residuals RMS: {np.sqrt(np.mean(R**2)):.6e}")
        print("="*70)
    
    # Return results dictionary
    return {
        'C': C,
        'ST': ST,
        'R': R,
        'D': D,
        'D_reconstructed': D_reconstructed,
        'model': mcrar,
        'n_iter': n_iter,
        'err': final_err,
        'converged': converged,
        'energy': energy,
        'err_history': mcrar.err,
        'n_components': n_components
    }


def visualize_mcr_results(results, df_data, figsize=(16, 12)):
    """
    Create comprehensive visualization of MCR-ALS results.
    
    Creates a multi-panel figure with:
    - Upper left (2×2): Concentration profiles vs spectrum number
    - Lower left (2×2): Resolved component spectra
    - Upper right top (1×2): Residuals summed across energy
    - Upper right bottom (1×2): Residuals summed across spectra
    - Lower right (2×2): 3D scatter plot of residuals
    
    Parameters:
    -----------
    results : dict
        Results dictionary from run_mcr_als() containing:
        - 'C': Concentration matrix
        - 'ST': Spectra matrix
        - 'R': Residuals matrix
        - 'energy': Energy values
    df_data : pandas.DataFrame
        Original data (for axis labels/limits)
    figsize : tuple, optional
        Figure size (default: (16, 12))
    
    Returns:
    --------
    matplotlib.figure.Figure
        The created figure
    """
    
    # Extract results
    C = results['C']
    ST = results['ST']
    R = results['R']
    energy = results['energy']
    n_components = results['n_components']
    
    # Create figure with 4×4 gridspec
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    gs = gridspec.GridSpec(4, 4, figure=fig)
    
    # --- UPPER LEFT [0:2, 0:2]: Concentration profiles ---
    ax_c = fig.add_subplot(gs[0:2, 0:2])
    
    spectra_indices = np.arange(1, C.shape[0] + 1)
    for i in range(n_components):
        ax_c.plot(spectra_indices, C[:, i], marker='o', markersize=4,
                 label=f'Component {i+1}', linewidth=2)
    
    ax_c.set_xlabel('Spectrum Number', fontweight='bold', fontsize=12)
    ax_c.set_ylabel('Concentration', fontweight='bold', fontsize=12)
    ax_c.set_title('Concentration Profiles', fontweight='bold', fontsize=14)
    ax_c.legend(frameon=True, fontsize=10)
    ax_c.grid(True, alpha=0.3)
    
    # --- LOWER LEFT [2:, 0:2]: Component spectra ---
    ax_s = fig.add_subplot(gs[2:, 0:2])
    
    for i in range(n_components):
        ax_s.plot(energy, ST[i, :], label=f'Component {i+1}', linewidth=2)
    
    ax_s.set_xlabel('Energy (eV)', fontweight='bold', fontsize=12)
    ax_s.set_ylabel('Absorbance', fontweight='bold', fontsize=12)
    ax_s.set_title('Resolved Component Spectra', fontweight='bold', fontsize=14)
    ax_s.legend(frameon=True, fontsize=10)
    ax_s.grid(True, alpha=0.3)
    
    # --- UPPER RIGHT TOP [0:1, 2:]: Residuals summed across energy ---
    ax_res_e = fig.add_subplot(gs[0:1, 2:])
    
    # Sum residuals across energy (for each spectrum)
    res_sum_energy = np.sum(np.abs(R), axis=1)
    
    ax_res_e.plot(spectra_indices, res_sum_energy, 'b-o', markersize=4, linewidth=2)
    ax_res_e.set_xlabel('Spectrum Number', fontweight='bold', fontsize=11)
    ax_res_e.set_ylabel('|Residual| (summed across energy)', fontweight='bold', fontsize=11)
    ax_res_e.set_title('Residuals Summed Across Energy', fontweight='bold', fontsize=12)
    ax_res_e.grid(True, alpha=0.3)
    
    # --- UPPER RIGHT BOTTOM [1:2, 2:]: Residuals summed across spectra ---
    ax_res_s = fig.add_subplot(gs[1:2, 2:])
    
    # Sum residuals across spectra (for each energy point)
    res_sum_spectra = np.sum(np.abs(R), axis=0)
    
    ax_res_s.plot(energy, res_sum_spectra, 'r-', linewidth=2)
    ax_res_s.set_xlabel('Energy (eV)', fontweight='bold', fontsize=11)
    ax_res_s.set_ylabel('|Residual| (summed across spectra)', fontweight='bold', fontsize=11)
    ax_res_s.set_title('Residuals Summed Across Spectra', fontweight='bold', fontsize=12)
    ax_res_s.grid(True, alpha=0.3)
    
    # --- LOWER RIGHT [2:, 2:]: 3D residuals scatter ---
    ax_3d = fig.add_subplot(gs[2:, 2:], projection='3d')
    
    # Create meshgrid for 3D plot
    spectrum_grid, energy_grid = np.meshgrid(spectra_indices, energy)
    
    # Flatten for scatter plot
    spectrum_flat = spectrum_grid.flatten()
    energy_flat = energy_grid.flatten()
    residual_flat = R.T.flatten()  # Transpose to match grid orientation
    
    # Color by residual magnitude
    colors = residual_flat
    scatter = ax_3d.scatter(spectrum_flat, energy_flat, residual_flat,
                           c=colors, cmap='coolwarm', s=10, alpha=0.6,
                           edgecolors='none')
    
    ax_3d.set_xlabel('Spectrum Number', fontweight='bold', fontsize=10)
    ax_3d.set_ylabel('Energy (eV)', fontweight='bold', fontsize=10)
    ax_3d.set_zlabel('Residual', fontweight='bold', fontsize=10)
    ax_3d.set_title('3D Residual Distribution', fontweight='bold', fontsize=12)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax_3d, pad=0.1, shrink=0.8)
    cbar.set_label('Residual Value', fontweight='bold', rotation=270, labelpad=20)
    
    # Adjust viewing angle
    ax_3d.view_init(elev=20, azim=45)
    
    plt.show()
    
    return fig



def create_results_dataframes(results):
    """
    Convert MCR-ALS results to pandas DataFrames for easy export/analysis.
    
    Parameters:
    -----------
    results : dict
        Results dictionary from run_mcr_als()
    
    Returns:
    --------
    dict
        Dictionary containing:
        - 'df_C': Concentration matrix as DataFrame
        - 'df_ST': Spectra matrix as DataFrame (transposed, energy × components)
        - 'df_R': Residuals matrix as DataFrame
    """
    
    C = results['C']
    ST = results['ST']
    R = results['R']
    energy = results['energy']
    n_components = results['n_components']
    
    # Create DataFrames
    df_C = pd.DataFrame(C, columns=[f'Component_{i+1}' for i in range(n_components)])
    df_C.index.name = 'Spectrum_Number'
    
    df_ST = pd.DataFrame(ST.T, index=energy, 
                         columns=[f'Component_{i+1}' for i in range(n_components)])
    df_ST.index.name = 'Energy'
    
    df_R = pd.DataFrame(R, columns=[f'Energy_{e}' for e in energy])
    df_R.index.name = 'Spectrum_Number'
    
    return {
        'df_C': df_C,
        'df_ST': df_ST,
        'df_R': df_R
    }


def plot_mcr_reconstruction_interactive(results, df_data, figsize=(10, 6)):
    """
    Interactive visualization of MCR-ALS reconstructed spectra vs original data.
    
    Uses dropdown widget to select which spectrum to visualize. Shows original
    data and reconstructed spectrum with individual component contributions.
    
    Parameters:
    -----------
    results : dict
        Results dictionary from run_mcr_als() containing:
        - 'C': Concentration matrix
        - 'ST': Spectra matrix
        - 'energy': Energy values
        - 'D': Original data matrix
        - 'n_components': Number of components
    df_data : pandas.DataFrame
        Original spectral data (for column names and energy axis)
    figsize : tuple, optional
        Figure size (default: (10, 6))
    
    Returns:
    --------
    dict
        Dictionary containing the interactive widget and dropdown reference
    
    Example:
    --------
    from mcr_visualization import plot_mcr_reconstruction_interactive
    
    # After running MCR-ALS
    widget_dict = plot_mcr_reconstruction_interactive(results, df_MCRALS)
    """
    
    # Extract results
    C = results['C']
    ST = results['ST']
    energy = results['energy']
    n_components = results['n_components']
    
    # Get spectrum options
    spectrum_columns = df_data.columns
    
    # Create dropdown for spectrum selection
    spectrum_dropdown = widgets.Dropdown(
        options=[(f'Spectrum {i+1}: {col}', i) for i, col in enumerate(spectrum_columns)],
        value=0,
        description='Select Spectrum:',
        disabled=False,
        style={'description_width': '120px'}
    )
    
    # Energy range sliders
    e_min = energy.min()
    e_max = energy.max()
    
    energy_min_slider = widgets.FloatSlider(
        value=e_min,
        min=e_min,
        max=e_max,
        step=(e_max - e_min) / 100,
        description='Energy Min:',
        disabled=False,
        style={'description_width': '120px'}
    )
    
    energy_max_slider = widgets.FloatSlider(
        value=e_max,
        min=e_min,
        max=e_max,
        step=(e_max - e_min) / 100,
        description='Energy Max:',
        disabled=False,
        style={'description_width': '120px'}
    )
    
    # Plot function
    def plot_reconstruction(spectrum_idx, emin, emax):
        plt.figure(figsize=figsize)
        
        # Original data
        original_spectrum = df_data.iloc[:, spectrum_idx].values
        plt.plot(energy, original_spectrum, 'k-', linewidth=2, 
                label='Original Data', zorder=3)
        
        # Reconstruct spectrum from components
        reconstructed = np.zeros(len(energy))
        for i in range(n_components):
            component_contribution = ST[i, :] * C[spectrum_idx, i]
            reconstructed += component_contribution
        
        # Plot reconstructed spectrum
        plt.plot(energy, reconstructed, 'r-', linewidth=2, 
                label='Reconstructed', alpha=0.8, zorder=2)
        
        # Calculate and display residual
        residual = original_spectrum - reconstructed
        rmse = np.sqrt(np.mean(residual**2))
        
        plt.plot(energy, residual, 'orange', linewidth=1.5, linestyle=':', 
                label=f'Residual (RMSE={rmse:.4e})', alpha=0.7, zorder=1)
        
        # Formatting
        plt.xlim(emin, emax)
        plt.xlabel('Photon Energy (eV)', fontweight='bold', fontsize=12)
        plt.ylabel('Norm. μ(E)x', fontweight='bold', fontsize=12)
        plt.title(f'MCR-ALS Reconstruction: Spectrum {spectrum_idx+1}', 
                 fontweight='bold', fontsize=14)
        plt.legend(frameon=True, fontsize=10)
        plt.grid(True, alpha=0.3)
        
        # Add horizontal line at zero for residual reference
        plt.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
        
        plt.show()
    
    # Create interactive widget
    interactive_widget = widgets.interactive_output(
        plot_reconstruction,
        {
            'spectrum_idx': spectrum_dropdown,
            'emin': energy_min_slider,
            'emax': energy_max_slider
        }
    )
    
    # Create layout
    controls = widgets.VBox([
        spectrum_dropdown,
        energy_min_slider,
        energy_max_slider
    ])
    
    display(widgets.VBox([controls, interactive_widget]))
    
    return {
        'spectrum': spectrum_dropdown,
        'energy_min': energy_min_slider,
        'energy_max': energy_max_slider,
        'output': interactive_widget
    }


def plot_mcr_reconstruction_with_components(results, df_data, spectrum_idx, 
                                           emin=None, emax=None, figsize=(10, 6)):
    """
    Plot MCR-ALS reconstruction showing individual component contributions.
    
    Non-interactive version that shows each component's contribution separately.
    
    Parameters:
    -----------
    results : dict
        Results dictionary from run_mcr_als()
    df_data : pandas.DataFrame
        Original spectral data
    spectrum_idx : int
        Index of spectrum to visualize (0-based)
    emin : float, optional
        Minimum energy for x-axis (default: data minimum)
    emax : float, optional
        Maximum energy for x-axis (default: data maximum)
    figsize : tuple, optional
        Figure size (default: (10, 6))
    
    Example:
    --------
    # Plot reconstruction for 15th spectrum with component breakdown
    plot_mcr_reconstruction_with_components(results, df_MCRALS, spectrum_idx=14)
    """
    
    # Extract results
    C = results['C']
    ST = results['ST']
    energy = results['energy']
    n_components = results['n_components']
    
    if emin is None:
        emin = energy.min()
    if emax is None:
        emax = energy.max()
    
    plt.figure(figsize=figsize)
    
    # Original data
    original_spectrum = df_data.iloc[:, spectrum_idx].values
    plt.plot(energy, original_spectrum, 'k-', linewidth=2.5, 
            label='Original Data', zorder=3)
    
    # Plot individual component contributions
    reconstructed = np.zeros(len(energy))
    for i in range(n_components):
        component_contribution = ST[i, :] * C[spectrum_idx, i]
        reconstructed += component_contribution
        plt.plot(energy, component_contribution, '--', linewidth=1.5, alpha=0.7,
                label=f'Component {i+1} (C={C[spectrum_idx, i]:.3f})')
    
    # Plot total reconstruction
    plt.plot(energy, reconstructed, 'r-', linewidth=2, 
            label='Total Reconstruction', alpha=0.8, zorder=2)
    
    # Plot residual
    residual = original_spectrum - reconstructed
    rmse = np.sqrt(np.mean(residual**2))
    plt.plot(energy, residual, 'orange', linewidth=1.5, linestyle=':', 
            label=f'Residual (RMSE={rmse:.4e})', alpha=0.7, zorder=1)
    
    # Formatting
    plt.xlim(emin, emax)
    plt.xlabel('Photon Energy (eV)', fontweight='bold', fontsize=12)
    plt.ylabel('Norm. μ(E)x', fontweight='bold', fontsize=12)
    plt.title(f'MCR-ALS Reconstruction with Components: Spectrum {spectrum_idx+1}', 
             fontweight='bold', fontsize=14)
    plt.legend(frameon=True, fontsize=9, loc='best')
    plt.grid(True, alpha=0.3)
    plt.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
    
    plt.show()


def save_mcr_results(mcr_results, save_dir, base_name):
    """
    Save MCR-ALS results to separate CSV files.
    
    Saves three files:
    1. Concentration matrix (C)
    2. Resolved component spectra (ST)
    3. Residuals matrix (R)
    
    Parameters:
    -----------
    mcr_results : dict
        Results from run_mcr_als() containing:
        - 'C': Concentration matrix
        - 'ST': Spectra matrix
        - 'R': Residuals matrix
        - 'energy': Energy values
        - 'n_components': Number of components
    save_dir : str
        Directory path where files will be saved
    base_name : str
        Base name for output files (will be appended with descriptors)
    
    Returns:
    --------
    dict : Dictionary containing paths to saved files
    
    Examples:
    ---------
    import os
    
    output_dir = os.path.join(os.getcwd(), 'mcr_results')
    base_name = 'SnO2_TPR_MCR'
    
    saved_files = save_mcr_results(
        mcr_results=results,
        save_dir=output_dir,
        base_name=base_name
    )
    
    # Files created:
    # - ./mcr_results/SnO2_TPR_MCR_concentrations.csv
    # - ./mcr_results/SnO2_TPR_MCR_spectra.csv
    # - ./mcr_results/SnO2_TPR_MCR_residuals.csv
    """
    
    # Create directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    
    # Extract data
    C = mcr_results['C']
    ST = mcr_results['ST']
    R = mcr_results['R']
    energy = mcr_results['energy']
    n_components = mcr_results['n_components']
    
    saved_files = {}
    
    # --- Save Concentration Matrix (C) ---
    # Rows = spectrum number, Columns = components
    df_C = pd.DataFrame(
        C,
        columns=[f'Component_{i+1}' for i in range(n_components)]
    )
    df_C.index.name = 'Spectrum_Number'
    
    c_file = os.path.join(save_dir, f"{base_name}_concentrations.csv")
    df_C.to_csv(c_file)
    saved_files['concentrations'] = c_file
    print(f"Saved concentrations to: {c_file}")
    
    # --- Save Spectra Matrix (ST) ---
    # Transpose so rows = energy, columns = components
    df_ST = pd.DataFrame(
        ST.T,
        index=energy,
        columns=[f'Component_{i+1}' for i in range(n_components)]
    )
    df_ST.index.name = 'Energy'
    
    st_file = os.path.join(save_dir, f"{base_name}_spectra.csv")
    df_ST.to_csv(st_file)
    saved_files['spectra'] = st_file
    print(f"Saved spectra to: {st_file}")
    
    # --- Save Residuals Matrix (R) ---
    # Rows = spectrum number, Columns = energy points
    df_R = pd.DataFrame(
        R,
        columns=energy
    )
    df_R.index.name = 'Spectrum_Number'
    df_R.columns.name = 'Energy'
    
    r_file = os.path.join(save_dir, f"{base_name}_residuals.csv")
    df_R.to_csv(r_file)
    saved_files['residuals'] = r_file
    print(f"Saved residuals to: {r_file}")
    
    # --- Save summary information ---
    summary_file = os.path.join(save_dir, f"{base_name}_summary.txt")
    with open(summary_file, 'w') as f:
        f.write("MCR-ALS Analysis Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Number of components: {n_components}\n")
        f.write(f"Number of spectra: {C.shape[0]}\n")
        f.write(f"Number of energy points: {len(energy)}\n")
        f.write(f"Energy range: {energy.min():.2f} - {energy.max():.2f} eV\n")
        f.write("\nConvergence information:\n")
        f.write(f"  Iterations: {mcr_results['n_iter']}\n")
        f.write(f"  Converged: {mcr_results['converged']}\n")
        if mcr_results['err'] is not None:
            f.write(f"  Final error: {mcr_results['err']:.6e}\n")
        f.write("\nResiduals statistics:\n")
        f.write(f"  RMS: {np.sqrt(np.mean(R**2)):.6e}\n")
        f.write(f"  Mean: {np.mean(R):.6e}\n")
        f.write(f"  Std: {np.std(R):.6e}\n")
        f.write(f"  Max: {np.max(np.abs(R)):.6e}\n")
    
    saved_files['summary'] = summary_file
    print(f"Saved summary to: {summary_file}")
    
    # Print summary
    print("\nSummary:")
    print(f"  Number of components: {n_components}")
    print(f"  Number of spectra: {C.shape[0]}")
    print(f"  Energy range: {energy.min():.2f} - {energy.max():.2f} eV")
    print(f"  All files saved to: {save_dir}")
    
    return saved_files




























