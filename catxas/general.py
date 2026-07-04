# -*- coding: utf-8 -*-
"""
Created on Wed Jun  1 15:09:30 2022

@author: ashoff
"""

##############################################################################

                                # Modules #
                        
##############################################################################

# File Handling
import os
import shutil
from pathlib import Path

#Other Functions
import re
import errno
import random


# Data organization
import pandas as pd
import numpy as np


##############################################################################

                        # NON-XAS FUNCTIONS #
                        
##############################################################################

def create_subdir(parent_dir, sub_dir):
    '''
    Fuction to make a subdirectory in specified directory. Checks to see if 
    the directory already exists, and eitehr makes it or doesn't. Updates
    command line to the status of the subdirectory.
    
    Parameters
    ----------
    parent_dir : STR
        directory to place subdirector
    sub_dir : STR
        name of subdirectory

    Returns
    -------
    newdir : str
        full path strin of created director

    '''

    newdir = os.path.join(parent_dir, sub_dir)

    try:
        os.mkdir(newdir)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            print("Directory Already Exists - Continuing Program")
        else:
            print ("Creation of the directory failed")
    else:
        print ("Successfully created subdirectory")
        
    return newdir


def find_nearest(array, value): 
    """
    Finds the index of the array that is closest to the requested value
    
    Returns: [index, array[index]]
    """
    array = np.asarray(array)
    
    idx = (np.abs(array - value)).argmin()
    
    return [idx, array[idx]]

def get_trailing_number(s):
    """
    Checks to see if there is a number at the end of string
    
    Parameters
    ----------
    s : string
            String to look for numbers at the end of

    Returns
    -------
    int
            Rumber at end of string, if none, return None

    """
    m = re.search(r'\d+$', s)
    return int(m.group()) if m else None
    
def interp_df(df, new_index):
    '''
    NEEDS Updatinng - index must be energy scale

    Parameters
    ----------
    df : TYPE
        DESCRIPTION.
    new_index : TYPE
        DESCRIPTION.

    Returns
    -------
    df_out : TYPE
        DESCRIPTION.

    '''
    """Return a new DataFrame with all columns values interpolated
    to the new_index values."""
    df_out = pd.DataFrame(index=new_index)
    df_out.index.name = df.index.name

    for colname, col in df.items():
        df_out[colname] = np.interp(new_index, df.index, col)

    return df_out


def mergeindex(df1, df2, method = 'time'):
    """
    interpolates df2 onto df1 index
    
    df1: dataframe wiht index used for reindexing. requires datetime index
    
    df2: dataframe to be reindexed. requires datetime index
    
    Note: if df1 index exceeds limits of df2, NaN will be returned in values that can not be interpoalted
    
    Return: df2 with df1 index 
    """
    
    # Update 07/01/2026 - Change in Pandas/Numpy is no longer allowing for interpolation of non=numeric columns
    
    #Old Code:
    #df2 = df2.reindex(df2.index.union(df1.index)).interpolate(method=method, limit_area = None).reindex(df1.index)
    
    # New code
    # 1. select only the numeric columbs from df 2:
    temp_df = df2.select_dtypes(include='number')
    
    # 2. get number of non-numeric columns in df2:
    non_number_cols_df2 = df2.select_dtypes(exclude=['number']).columns.tolist()
    
    # 3. Feedback to user if soem columns will not be interpolated:
    if len(non_number_cols_df2) != 0:
        print('Non-numeric columns found!')
        print('The following columns will be dropped during interpolation:')
        for line in non_number_cols_df2:
            print(f'\t{line}')
   
    # 4. Interpolate numeric columns of dataframe:
    df2 = temp_df.reindex(temp_df.index.union(df1.index)).interpolate(method=method, limit_area = None).reindex(df1.index)
    
    return df2

def parse_list(m, n):
    '''
    m = list of names
    
    n = how many items should be grouped together
    
    last value is a list of remainders
    
    returns a list of lists (lenght n) with the last list the modulo m%n (remainder)
    '''
    # using list comprehension
    x = [m[i:i + n] for i in range(0, len(m), n)]
    
    return x


def create_random_subset(source_dir, n_files, subset_name="subset of data for screening"):
    """
    Create a subdirectory with n random files copied from the source directory.
    
    Parameters:
    -----------
    source_dir : str
        Path to the source directory containing files to sample from
    n_files : int
        Number of random files to copy
    subset_name : str, optional
        Name of the subdirectory to create (default: "subset of data for screening")
    
    Returns:
    --------
    str or None
        Path to the created subset directory, or None if operation failed
    
    Examples:
    ---------
    # Create subset with 100 random files
    subset_dir = create_random_subset(
        source_dir=r"C:\data\all_spectra",
        n_files=100
    )
    
    # Use custom subset folder name
    subset_dir = create_random_subset(
        source_dir=r"C:\data\all_spectra",
        n_files=50,
        subset_name="test_data"
    )
    """
    
    # Convert to Path object
    source_path = Path(source_dir)
    
    # Verify source directory exists
    if not source_path.exists() or not source_path.is_dir():
        print(f"Error: The source directory '{source_dir}' does not exist.")
        return None
    
    # Create destination path as subdirectory of source
    dest_path = source_path / subset_name
    
    # Check if destination already exists
    if dest_path.exists():
        print(f"Warning: Subdirectory '{subset_name}' already exists in '{source_dir}'.")
        print("Please delete it first or choose a different name.")
        return None
    
    # Gather all files in the source directory (excluding folders and the subset dir)
    all_files = [f for f in source_path.iterdir() 
                 if f.is_file() and f.parent == source_path]
    total_files = len(all_files)
    
    print(f"Found {total_files} files in '{source_dir}'.")
    
    if total_files == 0:
        print("No files available to copy.")
        return None
    
    # Handle cases where requested n is larger than available files
    if n_files > total_files:
        print(f"Warning: Requested {n_files} files, but only {total_files} exist.")
        print(f"Copying all {total_files} files instead.")
        n_files = total_files
    
    # Pick n unique random files
    random_selection = random.sample(all_files, n_files)
    
    # Create the destination directory
    dest_path.mkdir(parents=True, exist_ok=True)
    
    # Copy the selected files
    print(f"\nCopying {n_files} random files to '{subset_name}'...")
    for file_path in random_selection:
        shutil.copy2(file_path, dest_path / file_path.name)
    
    print(f"✓ Successfully copied {n_files} files to: {dest_path}")
    
    return str(dest_path)


def delete_subset(source_dir, subset_name="subset of data for screening", confirm=False):
    """
    Delete the subset subdirectory and all its contents.
    
    Parameters:
    -----------
    source_dir : str
        Path to the parent directory containing the subset folder
    subset_name : str, optional
        Name of the subdirectory to delete (default: "subset of data for screening")
    confirm : bool, optional
        If True, asks for confirmation before deleting (default: False for notebook use)
    
    Returns:
    --------
    bool
        True if folder was deleted, False otherwise
    
    Examples:
    ---------
    # Delete the subset folder
    delete_subset(source_dir=r"C:\data\all_spectra")
    
    # Delete with confirmation prompt
    delete_subset(source_dir=r"C:\data\all_spectra", confirm=True)
    
    # Delete custom-named subset
    delete_subset(
        source_dir=r"C:\data\all_spectra",
        subset_name="test_data"
    )
    """
    
    # Convert to Path object
    source_path = Path(source_dir)
    subset_path = source_path / subset_name
    
    # Check if subset exists
    if not subset_path.exists():
        print(f"Subset folder does not exist: {subset_path}")
        return False
    
    # Check if it's actually a directory
    if not subset_path.is_dir():
        print(f"Path is not a directory: {subset_path}")
        return False
    
    # Count contents
    try:
        contents = list(subset_path.iterdir())
        n_items = len(contents)
    except PermissionError:
        print(f"Permission denied to access: {subset_path}")
        return False
    
    # Confirmation prompt if requested
    if confirm:
        print(f"\nSubset folder: {subset_path}")
        print(f"Contains: {n_items} items")
        
        if n_items > 0:
            print("\nContents (first 10):")
            for item in contents[:10]:
                print(f"  - {item.name}")
            if n_items > 10:
                print(f"  ... and {n_items - 10} more items")
        
        response = input("\nDelete this subset folder and all its contents? (yes/no): ")
        
        if response.lower() not in ['yes', 'y']:
            print("Deletion cancelled.")
            return False
    
    # Delete the folder
    try:
        shutil.rmtree(subset_path)
        print(f"✓ Successfully deleted subset: {subset_path}")
        return True
    except Exception as e:
        print(f"Error deleting folder: {e}")
        return False