#!/bin/bash
#
#$ -S /bin/bash
#$ -v TST=abc
#$ -M hringbauer@ist.ac.at
#$ -N "Discrete5"
#$ -m ea
#$ -l mf=8G
#$ -l mem_free=8G
#$ -l h_vmem=8G
#$ -l h_rt=60:00:00
#$ -cwd
#$ -t 1-100:1

export OMP_NUM_THREADS=1  					# Sets Number of Threads to 1.
python multi_run_hetero.py $SGE_TASK_ID		# Runs the Script.
# echo $SGE_TASK_ID
