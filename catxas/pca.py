# -*- coding: utf-8 -*-
"""
Created on Thu Jul  2 10:20:12 2026

@author: ashoff
"""

import os

import numpy as np
import pandas as pd


import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

import ipywidgets as widgets
from IPython.display import display

from sklearn.decomposition import PCA, TruncatedSVD
from kneed import KneeLocator

#From Catxas
import plot as pfcts


def select_spectral_range(df, xlabel='Photon energy (eV)', ylabel='Norm. μ(E)x', 
                          figsize=(8, 6)):
    """
    Interactive widget for selecting energy and spectrum ranges from a dataframe.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with energy values as index and spectra as columns
    xlabel : str, optional
        Label for x-axis (default: 'Photon energy (eV)')
    ylabel : str, optional
        Label for y-axis (default: 'Norm. μ(E)x')
    figsize : tuple, optional
        Figure size as (width, height) (default: (8, 6))
    
    Returns:
    --------
    dict : Dictionary containing the interactive widget and dropdown references
           Access selected values via widget.kwargs after interaction
    """
    
    # Energy range options
    e_range = df.index.values
    
    # Spectrum range options
    s_range = list(range(len(df.columns)))
    
    # Style for consistent widget appearance
    widget_style = {'description_width': '120px'}
    
    # Create dropdown widgets
    e_min_drop = widgets.Dropdown(
        options=e_range,
        value=e_range[0],
        description='Energy Min:',
        disabled=False,
        style=widget_style
    )
    
    e_max_drop = widgets.Dropdown(
        options=e_range,
        value=e_range[-1],
        description='Energy Max:',  # Fixed: was 'Energy Min'
        disabled=False,
        style=widget_style
    )
    
    s_min_drop = widgets.Dropdown(
        options=s_range,
        value=s_range[0],
        description='Spectrum Start:',
        disabled=False,
        style=widget_style
    )
    
    s_max_drop = widgets.Dropdown(
        options=s_range,
        value=s_range[-1],
        description='Spectrum End:',
        disabled=False,
        style=widget_style
    )
    
    # Plot function
    def plot_function(emin, emax, smin, smax):
        plt.figure(figsize=figsize)
        plt.plot(df.loc[emin:emax].iloc[:, smin:smax+1])
        plt.xlabel(xlabel, fontweight='bold')
        plt.ylabel(ylabel, fontweight='bold')
        plt.grid(False)
        plt.show()
    
    # Create interactive widget
    interactive_plot = widgets.interactive(
        plot_function, 
        emin=e_min_drop, 
        emax=e_max_drop, 
        smin=s_min_drop, 
        smax=s_max_drop
    )
    
    # Display the widget
    display(interactive_plot)
    
    # Return widget object for programmatic access if needed
    return {
        'widget': interactive_plot,
        'e_min': e_min_drop,
        'e_max': e_max_drop,
        's_min': s_min_drop,
        's_max': s_max_drop
    }


def perform_pca_analysis(df_pca, mean_center=True, n_components=None):
    """
    Perform PCA analysis with optional mean centering.
    
    Parameters:
    -----------
    df_pca : pandas.DataFrame
        DataFrame containing spectral data where:
        - ROWS = energy points (features)
        - COLUMNS = spectra/samples (observations)
    mean_center : bool, optional
        Whether to mean-center the data before PCA (default: True)
        If True: uses PCA (mean-centered)
        If False: uses TruncatedSVD (no mean-centering)
    n_components : int, optional
        Number of components. If None, uses min(n_spectra, n_energy_points)
        Maximum allowed is min(n_spectra, n_energy_points)
    
    Returns:
    --------
    dict : Dictionary containing all PCA results and DataFrames
    """
    
    # Get dimensions
    n_energy_points = df_pca.shape[0]  # Number of rows (features)
    n_spectra = df_pca.shape[1]         # Number of columns (samples)
    
    print(f"Input DataFrame shape: {df_pca.shape}")
    print(f"Number of energy points (features): {n_energy_points}")
    print(f"Number of spectra (samples): {n_spectra}")
    
    # Set number of components
    max_components = min(n_spectra, n_energy_points)
    if n_components is None:
        n_components = n_spectra  # Use all spectra
    
    if n_components > max_components:
        print(f"Warning: n_components ({n_components}) reduced to maximum allowed ({max_components})")
        n_components = max_components
    
    # Get energy range from dataframe index
    e_min_value = df_pca.index.min()
    e_max_value = df_pca.index.max()
    
    # Transpose for sklearn (expects samples as rows, features as columns)
    # After transpose: rows = spectra (samples), columns = energy points (features)
    data_transposed = df_pca.T
    
    print(f"Transposed shape for sklearn: {data_transposed.shape}")
    print("(rows=spectra, columns=energy points)")
    
    if mean_center:
        print("\nUsing PCA with mean-centering...")
        # Standard PCA (includes mean-centering)
        model = PCA(n_components=n_components)
        model.fit(data_transposed)
        
        # Get components and transform
        scores = model.transform(data_transposed)
        eigenspectra = model.components_
        explained_variance_ratio = model.explained_variance_ratio_
        covar = model.get_covariance()
        
    else:
        print("\nUsing SVD without mean-centering...")
        # TruncatedSVD (no mean-centering)
        model = TruncatedSVD(n_components=n_components)
        model.fit(data_transposed)
        
        # Get components and transform
        scores = model.transform(data_transposed)
        eigenspectra = model.components_
        explained_variance_ratio = model.explained_variance_ratio_
        
        # Manually compute covariance without mean-centering
        covar = np.cov(data_transposed.T, bias=True)
    
    # Generate DataFrames
    index_names = df_pca.columns  # Spectrum names/indices
    df_pca_score = pd.DataFrame(scores, index=index_names)
    
    # Cumulative Variance Explained
    pca_cve = np.cumsum(explained_variance_ratio)
    df_pca_CVE = pd.DataFrame(pca_cve, columns=['Cumulative Variance'])
    
    # Eigenspectra (transpose back to match original orientation)
    # Each component is a row, transpose so each component is a column
    # and energy points are rows (matching original df_pca orientation)
    df_pca_eigen = pd.DataFrame(eigenspectra.T, index=df_pca.index)
    
    # Print feedback
    print('\nAnalysis Results:')
    print(f'Mean-centering: {mean_center}')
    print(f'Number of components extracted: {n_components}')
    print(f'Size of Eigenspectra array: {np.shape(eigenspectra)} (components × energy_points)')
    print(f'Length of CVE list: {len(pca_cve)}')
    print(f'Size of Score array: {np.shape(scores)} (spectra × components)')
    print(f'Size of Covariance Matrix: {np.shape(covar)}')
    print(f'Energy range of Spectra [eV]: {e_min_value}-{e_max_value}')
    
    # Return everything
    return {
        'model': model,
        'scores': scores,
        'df_scores': df_pca_score,
        'eigenspectra': eigenspectra,
        'df_eigenspectra': df_pca_eigen,
        'cve': pca_cve,
        'df_cve': df_pca_CVE,
        'covariance': covar,
        'explained_variance_ratio': explained_variance_ratio,
        'mean_centered': mean_center
    }


def plot_pca_results(pca_results, n_eigenspectra=10, spacing=0.5, 
                     figsize=(12, 5)):
    """
    Visualize PCA results with scree plot and eigenspectra.
    
    Parameters:
    -----------
    pca_results : dict
        Dictionary returned from perform_pca_analysis() containing:
        - 'cve': cumulative variance explained array
        - 'df_eigenspectra': DataFrame of eigenspectra (energy × components)
        - 'eigenspectra': raw eigenspectra array (components × energy)
    n_eigenspectra : int, optional
        Number of eigenspectra to plot (default: 10)
    spacing : float, optional
        Vertical spacing between eigenspectra (default: 0.5)
    figsize : tuple, optional
        Figure size as (width, height) in inches (default: (12, 5))
    
    Returns:
    --------
    fig, axes : matplotlib figure and axes objects
    suggested_components : int or None
        The suggested number of components (knee - 1) (None if not found)
    """
    
    # Extract data from results
    pca_cve = pca_results['cve']
    df_pca_eigen = pca_results['df_eigenspectra']
    pca_eigen = pca_results['eigenspectra']
    energy = df_pca_eigen.index.values
    
    # Create figure with 1 row, 2 columns
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    gs = gridspec.GridSpec(1, 2, figure=fig)
    
    # --- LEFT PLOT: Scree Plot (CVE) ---
    ax1 = fig.add_subplot(gs[0, 0])
    
    component_numbers = np.arange(1, len(pca_cve) + 1)
    
    ax1.scatter(component_numbers, pca_cve, c='purple', s=50, zorder=3)
    ax1.plot(component_numbers, pca_cve, color='purple', linewidth=3, zorder=2)
    
    # Find the knee point using KneeLocator
    suggested_components = None
    try:
        kneedle = KneeLocator(
            component_numbers, 
            pca_cve, 
            curve='concave',  # CVE curve is concave
            direction='increasing',  # CVE increases
            S=1.0  # Sensitivity parameter (1.0 is default)
        )
        
        if kneedle.knee is not None:
            knee_component = kneedle.knee
            knee_cve = pca_cve[knee_component - 1]  # -1 for 0-based indexing
            
            # Use knee - 1 as the suggested number of components
            suggested_components = max(1, knee_component - 1)  # Ensure at least 1
            suggested_cve = pca_cve[suggested_components - 1]  # -1 for 0-based indexing
            
            # Annotate at the knee point with both knee and suggested info
            annotation_text = (f'Knee: Component {knee_component} (CVE = {knee_cve:.4f})\n'
                             f'Suggested: {suggested_components} components (CVE = {suggested_cve:.4f})')
            
            ax1.annotate(annotation_text,
                        xy=(knee_component, knee_cve),
                        xytext=(30, -40), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0',
                                      color='red', lw=2),
                        fontsize=10, fontweight='bold')
            
            print(f"Knee detected at component {knee_component} (CVE = {knee_cve:.4f})")
            print(f"Suggested number of components: {suggested_components} (CVE = {suggested_cve:.4f})")
        else:
            print("No clear knee point detected")
            
    except Exception as e:
        print(f"Knee detection failed: {e}")
    
    # Set x-axis limits to show first several components clearly
    max_x = min(max(8, knee_component + 3 if kneedle.knee else 8), len(pca_cve))
    ax1.set_xlim(-0.5, max_x + 0.5)
    
    ax1.set_xlabel('Number of Components', fontweight='bold', fontsize=12)
    ax1.set_ylabel('CVE', fontweight='bold', fontsize=12)
    ax1.set_title('Scree Plot', fontweight='bold', fontsize=14)
    ax1.grid(True, alpha=0.3)
    
    # --- RIGHT PLOT: Eigenspectra ---
    ax2 = fig.add_subplot(gs[0, 1])
    
    # Limit to available components
    n_plot = min(n_eigenspectra, pca_eigen.shape[0])
    
    # Calculate offsets for y-axis spacing
    y_offsets = np.arange(n_plot) * spacing
    
    cmap = plt.get_cmap('plasma')
    
    for i in range(n_plot):
        color = cmap(i / n_plot)
        ax2.plot(energy, pca_eigen[i, :] + y_offsets[i], 
                label=f'Component {i+1}', color=color, linewidth=2)
    
    ax2.set_xlabel('Photon Energy (eV)', fontweight='bold', fontsize=12)
    ax2.set_ylabel('Eigenspectra (offset)', fontweight='bold', fontsize=12)
    ax2.set_title(f'First {n_plot} Eigenspectra', fontweight='bold', fontsize=14)
    ax2.grid(True, alpha=0.3, axis='x')
    
    plt.show()
    
    return fig, (ax1, ax2), suggested_components


def plot_pca_reconstruction(pca_results, df_original, spectrum_index, 
                           n_components, figsize=(12, 8)):
    """
    Plot PCA reconstruction of a selected spectrum using specified number of components.
    
    Parameters:
    -----------
    pca_results : dict
        Dictionary returned from perform_pca_analysis() containing:
        - 'model': the fitted PCA or TruncatedSVD model
        - 'df_scores': DataFrame of PCA scores
        - 'df_eigenspectra': DataFrame of eigenspectra
        - 'mean_centered': boolean indicating if mean-centering was used
    df_original : pandas.DataFrame
        Original dataframe (rows = energy, columns = spectra)
    spectrum_index : int or str
        Index/column name of the spectrum to reconstruct
    n_components : int
        Number of components to use for reconstruction
    figsize : tuple, optional
        Figure size as (width, height) in inches (default: (12, 8))
    
    Returns:
    --------
    dict : Dictionary containing reconstruction data
        - 'original': original spectrum
        - 'reconstructed': reconstructed spectrum
        - 'cumulative_components': cumulative sum of components (before adding mean)
        - 'mean': mean spectrum (if mean-centered, else zeros)
    """
    
    # Extract data from results
    model = pca_results['model']
    df_scores = pca_results['df_scores']
    df_eigenspectra = pca_results['df_eigenspectra']
    mean_centered = pca_results['mean_centered']
    
    # Get energy values
    energy = df_original.index.values
    e_min = energy[0]
    e_max = energy[-1]
    
    # Get original spectrum
    original_spectrum = df_original[spectrum_index].values
    
    # Initialize reconstruction
    reconstructed_cumulative = np.zeros(len(energy))
    
    # Reconstruct spectrum using selected components
    for i in range(n_components):
        component_contribution = (df_eigenspectra.iloc[:, i].values * 
                                 df_scores.loc[spectrum_index, i])
        reconstructed_cumulative += component_contribution
    
    # Get mean spectrum (or zeros if not mean-centered)
    if mean_centered:
        mean_spectrum = model.mean_
    else:
        mean_spectrum = np.zeros(len(energy))
    
    # Final reconstruction
    reconstructed_spectrum = reconstructed_cumulative + mean_spectrum
    
    # Calculate residual
    residual = original_spectrum - reconstructed_spectrum
    rmse = np.sqrt(np.mean(residual**2))
    
    # Create plot
    plt.figure(figsize=figsize)
    
    # Plot original data
    plt.scatter(energy, original_spectrum, s=10, c='k', 
               label='Original Data', zorder=3)
    
    # Plot mean (if mean-centered)
    if mean_centered:
        plt.plot(energy, mean_spectrum, c='b', linewidth=2,
                label='PCA Mean', linestyle='--', alpha=0.7)
    
    # Plot cumulative components (before adding mean)
    plt.plot(energy, reconstructed_cumulative, c='g', linewidth=2,
            label=f'Cumulative Components (n={n_components})', alpha=0.7)
    
    # Plot final reconstruction
    plt.plot(energy, reconstructed_spectrum, c='r', linewidth=3,
            label='Reconstructed Spectrum')
    
    # Plot residuals
    plt.plot(energy, residual, c='orange', linewidth=2,
            label=f'Residual (RMSE={rmse:.6f})', linestyle=':', alpha=0.8)
    
    # Add horizontal line at zero for residual reference
    plt.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
    
    plt.xlim(e_min, e_max)
    plt.xlabel('Photon Energy (eV)', fontweight='bold', fontsize=12)
    plt.ylabel('Norm. μ(E)x', fontweight='bold', fontsize=12)
    plt.title(f'PCA Reconstruction: Spectrum {spectrum_index} using {n_components} components',
             fontweight='bold', fontsize=14)
    plt.legend(frameon=False, fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.show()
    
    # Return reconstruction data
    return {
        'original': original_spectrum,
        'reconstructed': reconstructed_spectrum,
        'cumulative_components': reconstructed_cumulative,
        'mean': mean_spectrum,
        'residual': residual,
        'rmse': rmse
    }


def interactive_pca_reconstruction(pca_results, df_original, figsize=(12, 8)):
    """
    Create interactive widget for exploring PCA reconstructions.
    
    Parameters:
    -----------
    pca_results : dict
        Dictionary returned from perform_pca_analysis()
    df_original : pandas.DataFrame
        Original dataframe (rows = energy, columns = spectra)
    figsize : tuple, optional
        Figure size as (width, height) in inches (default: (12, 8))
    
    Returns:
    --------
    interactive widget
    """
    
    # Get available spectra and components
    spectrum_options = list(df_original.columns)
    max_components = pca_results['df_eigenspectra'].shape[1]
    component_options = list(range(1, max_components + 1))
    
    # Style for widgets
    widget_style = {'description_width': '150px'}
    
    # Create dropdown for spectrum selection
    spectrum_dropdown = widgets.Dropdown(
        options=spectrum_options,
        value=spectrum_options[0],
        description='Select Spectrum:',
        disabled=False,
        style=widget_style
    )
    
    # Create dropdown for number of components
    component_dropdown = widgets.Dropdown(
        options=component_options,
        value=min(3, max_components),  # Default to 3 or max available
        description='Number of Components:',
        disabled=False,
        style=widget_style
    )
    
    # Wrapper function for interactive
    def update_plot(spectrum_idx, n_comps):
        plot_pca_reconstruction(pca_results, df_original, spectrum_idx, 
                               n_comps, figsize=figsize)
    
    # Create interactive widget with manual display control
    interactive_widget = widgets.interactive_output(
        update_plot,
        {'spectrum_idx': spectrum_dropdown, 'n_comps': component_dropdown}
    )
    
    # Create layout with controls and output
    controls = widgets.VBox([spectrum_dropdown, component_dropdown])
    display(widgets.VBox([controls, interactive_widget]))
    
    return {'spectrum': spectrum_dropdown, 'components': component_dropdown, 'output': interactive_widget}


def compare_pca_svd(pca_results, svd_results, df_original, n_components=5, 
                    figsize=(10, 10)):
    """
    Compare eigenspectra from PCA (mean-centered) and TruncatedSVD (non-mean-centered).
    
    The key insight: TruncatedSVD's first component often captures what would be
    the "mean" in PCA, so we compare:
    - PCA mean vs SVD component 1
    - PCA component 1 vs SVD component 2
    - PCA component 2 vs SVD component 3, etc.
    
    Parameters:
    -----------
    pca_results : dict
        Results from perform_pca_analysis() with mean_center=True
    svd_results : dict
        Results from perform_pca_analysis() with mean_center=False
    df_original : pandas.DataFrame
        Original dataframe for energy axis
    n_components : int, optional
        Number of components to compare (default: 5)
    figsize : tuple, optional
        Figure size (default: (10, 10))
    
    Returns:
    --------
    dict : Comparison metrics including correlation coefficients
    """
    
    # Extract data
    pca_mean = pca_results['model'].mean_
    pca_eigen = pca_results['df_eigenspectra']
    svd_eigen = svd_results['df_eigenspectra']
    energy = df_original.index.values
    
    # Number of comparisons (limited by available components)
    n_compare = min(n_components, pca_eigen.shape[1], svd_eigen.shape[1] - 1)
    
    # Create figure with subplots
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    gs = gridspec.GridSpec(n_compare + 1, 1, figure=fig)
    
    # Store correlation coefficients
    correlations = {}
    
    # --- First row: Compare PCA mean vs SVD component 1 ---
    ax = fig.add_subplot(gs[0, 0])
    
    svd_comp1 = svd_eigen.iloc[:, 0].values
    
    # Calculate correlation
    corr_mean = np.corrcoef(pca_mean, svd_comp1)[0, 1]
    correlations['mean_vs_svd1'] = corr_mean
    
    # Plot overlay
    ax.plot(energy, pca_mean, 'b-', linewidth=2, label='PCA Mean', alpha=0.7)
    ax.plot(energy, svd_comp1, 'r--', linewidth=2, label='SVD Component 1', alpha=0.7)
    ax.set_xlabel('Photon Energy (eV)', fontweight='bold')
    ax.set_ylabel('Value', fontweight='bold')
    ax.set_title(f'PCA Mean vs SVD Component 1 (Corr: {corr_mean:.4f})', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # --- Subsequent rows: Compare PCA components vs SVD components (offset by 1) ---
    for i in range(n_compare):
        ax = fig.add_subplot(gs[i + 1, 0])
        
        pca_comp = pca_eigen.iloc[:, i].values
        svd_comp = svd_eigen.iloc[:, i + 1].values  # Offset by 1
        
        # Calculate correlation
        corr = np.corrcoef(pca_comp, svd_comp)[0, 1]
        correlations[f'pca{i+1}_vs_svd{i+2}'] = corr
        
        # Plot overlay
        ax.plot(energy, pca_comp, 'b-', linewidth=2, 
                label=f'PCA Component {i+1}', alpha=0.7)
        ax.plot(energy, svd_comp, 'r--', linewidth=2, 
                label=f'SVD Component {i+2}', alpha=0.7)
        ax.set_xlabel('Photon Energy (eV)', fontweight='bold')
        ax.set_ylabel('Value', fontweight='bold')
        ax.set_title(f'PCA Comp {i+1} vs SVD Comp {i+2} (Corr: {corr:.4f})', fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.show()
    
    # Print summary
    print("Correlation Coefficients:")
    print(f"  PCA Mean vs SVD Component 1: {correlations['mean_vs_svd1']:.6f}")
    for i in range(n_compare):
        key = f'pca{i+1}_vs_svd{i+2}'
        print(f"  PCA Comp {i+1} vs SVD Comp {i+2}: {correlations[key]:.6f}")
    
    return {
        'correlations': correlations,
        'pca_mean': pca_mean,
        'svd_component1': svd_comp1
    }


def plot_pca_scores_3d(pca_results, df_original, figsize=(12, 10), 
                       colormap='viridis'):
    """
    3D scatter plot of spectra in PCA space (first 3 components).
    This shows how your spectra are distributed in the reduced space.
    
    Parameters:
    -----------
    pca_results : dict
        Results from perform_pca_analysis()
    df_original : pandas.DataFrame
        Original dataframe (for spectrum labels)
    figsize : tuple, optional
        Figure size (default: (12, 10))
    colormap : str, optional
        Matplotlib colormap name (default: 'viridis')
        Options: 'viridis', 'plasma', 'inferno', 'magma', 'cividis',
                 'twilight', 'rainbow', 'jet', 'coolwarm', etc.
    """
    
    df_scores = pca_results['df_scores']
    
    # Extract first 3 component scores
    pc1 = df_scores.iloc[:, 0].values
    pc2 = df_scores.iloc[:, 1].values
    pc3 = df_scores.iloc[:, 2].values if df_scores.shape[1] >= 3 else np.zeros_like(pc1)
    
    # Get variance explained
    var_explained = pca_results['explained_variance_ratio']
    
    # Get spectrum indices/names
    spectrum_indices = df_original.columns
    n_spectra = len(spectrum_indices)
    
    # Create 3D plot
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')
    
    # Color spectra by their index (time/sequence) using compatible get_cmap
    cmap = pfcts.get_cmap(n_spectra, name=colormap)
    colors = cmap(np.linspace(0, 1, n_spectra))
    
    scatter = ax.scatter(pc1, pc2, pc3, c=colors, s=100, alpha=0.7, 
                        edgecolors='black', linewidth=1)
    
    # Draw axes through origin
    ax.plot([0, 0], [0, 0], [min(pc3), max(pc3)], 'k--', alpha=0.3, linewidth=1)
    ax.plot([0, 0], [min(pc2), max(pc2)], [0, 0], 'k--', alpha=0.3, linewidth=1)
    ax.plot([min(pc1), max(pc1)], [0, 0], [0, 0], 'k--', alpha=0.3, linewidth=1)
    
    ax.set_xlabel(f'PC1 ({var_explained[0]*100:.1f}% var)', fontweight='bold', fontsize=12)
    ax.set_ylabel(f'PC2 ({var_explained[1]*100:.1f}% var)', fontweight='bold', fontsize=12)
    ax.set_zlabel(f'PC3 ({var_explained[2]*100:.1f}% var)' if len(var_explained) >= 3 else 'PC3', 
                  fontweight='bold', fontsize=12)
    ax.set_title(f'Spectra in PCA Space - {n_spectra} spectra', fontweight='bold', fontsize=14)
    
    # Add colorbar showing spectrum sequence
    sm = plt.cm.ScalarMappable(cmap=cmap, 
                               norm=plt.Normalize(vmin=0, vmax=n_spectra-1))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, pad=0.1, shrink=0.8)
    cbar.set_label('Spectrum Index (0 to {})'.format(n_spectra-1), 
                   fontweight='bold', rotation=270, labelpad=20)
    
    plt.show()
    
    print("\nPlot Information:")
    print(f"Total spectra: {n_spectra}")
    print("Each point represents one spectrum")
    print(f"Colors: gradient from spectrum 0 to spectrum {n_spectra-1}")
    print(f"Colormap: {colormap}")
    print("Position: determined by projection onto first 3 PCs")
    
    return fig, ax


def save_pca_results(pca_results, save_dir, base_name):
    """
    Save PCA results to separate CSV files.
    
    Saves three files:
    1. Eigenspectra (and mean if mean-centered)
    2. Cumulative Variance Explained (CVE)
    3. Scores
    
    Parameters:
    -----------
    pca_results : dict
        Results from perform_pca_analysis() containing:
        - 'df_eigenspectra': DataFrame of eigenspectra
        - 'df_cve': DataFrame of cumulative variance explained
        - 'df_scores': DataFrame of scores
        - 'mean_centered': boolean
        - 'model': PCA or TruncatedSVD model (for mean if applicable)
    save_dir : str
        Directory path where files will be saved (will be created if doesn't exist)
    base_name : str
        Base name for output files (will be appended with descriptors)
    
    Returns:
    --------
    dict : Dictionary containing paths to saved files
    
    Examples:
    ---------
    import os
    
    output_dir = os.path.join(os.getcwd(), 'pca_results')
    base_name = 'SnO2_TPR_PCA'
    
    saved_files = save_pca_results(
        pca_results=results,
        save_dir=output_dir,
        base_name=base_name
    )
    
    # Files created:
    # - ./pca_results/SnO2_TPR_PCA_eigenspectra_with_mean.csv
    # - ./pca_results/SnO2_TPR_PCA_CVE.csv
    # - ./pca_results/SnO2_TPR_PCA_scores.csv
    """
    
    # Create directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    
    # Extract data
    df_eigenspectra = pca_results['df_eigenspectra']
    df_cve = pca_results['df_cve']
    df_scores = pca_results['df_scores']
    mean_centered = pca_results['mean_centered']
    
    saved_files = {}
    
    # --- Save Eigenspectra ---
    if mean_centered:
        # Include mean as a separate column
        model = pca_results['model']
        mean_spectrum = model.mean_
        
        # Create DataFrame with mean + eigenspectra
        df_eigen_save = df_eigenspectra.copy()
        df_eigen_save.insert(0, 'PCA_Mean', mean_spectrum)
        
        eigenspectra_file = os.path.join(save_dir, f"{base_name}_eigenspectra_with_mean.csv")
        df_eigen_save.to_csv(eigenspectra_file)
        saved_files['eigenspectra'] = eigenspectra_file
        print(f"Saved eigenspectra (with mean) to: {eigenspectra_file}")
    else:
        eigenspectra_file = os.path.join(save_dir, f"{base_name}_eigenspectra.csv")
        df_eigenspectra.to_csv(eigenspectra_file)
        saved_files['eigenspectra'] = eigenspectra_file
        print(f"Saved eigenspectra to: {eigenspectra_file}")
    
    # --- Save CVE ---
    cve_file = os.path.join(save_dir, f"{base_name}_CVE.csv")
    df_cve.to_csv(cve_file)
    saved_files['cve'] = cve_file
    print(f"Saved CVE to: {cve_file}")
    
    # --- Save Scores ---
    scores_file = os.path.join(save_dir, f"{base_name}_scores.csv")
    df_scores.to_csv(scores_file)
    saved_files['scores'] = scores_file
    print(f"Saved scores to: {scores_file}")
    
    # Print summary
    print("\nSummary:")
    print(f"  Mean-centered: {mean_centered}")
    print(f"  Number of components: {df_eigenspectra.shape[1]}")
    print(f"  Number of spectra: {df_scores.shape[0]}")
    print(f"  All files saved to: {save_dir}")
    
    return saved_files








