'''
Created on 27.01.2015
The Grid class; basically two matrices (one per chromosome) of lists for blocks sitting on every node.
Contains methods for updating one generation back in time and scanning for IBD
Also a class inheriting from Grid to a Grid allowing for growing/declining populations
by varying the number of chromosomes at every grid. Contains a factory method to produce this
Grid_Grow class
@author: hringbauer
'''
from blockpiece import BlPiece, Multi_Bl
from operator import attrgetter
from random import random
from parent_draw import DrawParent
import bisect
import numpy as np
import matplotlib.pyplot as plt
from timeit import default_timer as timer
from analysis import torus_distance
from mle_analysis import MLE_analyse
from random import shuffle


###################################################################################


class Grid(object):
# Object for the Data-Grid. Contains matrix of lists for chromosomal pieces and methods to update it.    
    chrom_l = 150  # Length of the chromosome
    gridsize = 90  # 180/2  # 160 # 180
    sample_steps = 2  # 6/2  # 4
    grid = []  # Will become the Grid-Matrix for Chromosomes
    grid1 = []  # Will become the Grid-Matrix for previous generation
    IBD_blocks = []  # Detected IBD-blocks 
    rec_rate = 100.0  # Everything is measured in CentiMorgan; Float!
    dispmode = "laplace"  # normal/uniform/laplace/demes
    sigma = 0.965   #sigma = 1.98      
    IBD_treshold = 4.0  # Threshold over which IBD is detected.
    delete = True  # If TRUE: blocks below threshold are deleted
    start_list = []  # Remember where initial chromosomes sat
    update_list = []  # Positions which need updating
    t = 0  # Time in generations back
    drawlist_length = 100000  # Variable for how many random Variables are drawn simultaneously
    
    drawer = 0  # Object for drawing parents   
    
    def __init__(self):  # Initializes an empty grid
        self.grid = np.empty((self.gridsize, self.gridsize, 2), dtype=np.object)  # Create empty array of objects, one for each chromosome
        self.grid1 = np.empty((self.gridsize, self.gridsize, 2), dtype=np.object)  # Creates empty array of object for previous generation
        
        drawer = DrawParent(self.drawlist_length, self.sigma, self.gridsize)  # Generate Drawer object
        self.drawer = drawer.choose_drawer(self.dispmode)
    
    def set_samples(self, position_list=0):
        '''Sets sample chromosomes on the grid'''          
        if position_list == 0:  # In case no position list given        
            position_list = [(i + self.sample_steps / 2, j + self.sample_steps / 2, 0) for i 
                             in range(0, self.gridsize, self.sample_steps) for j in range(0, self.gridsize, self.sample_steps)]
        self.set_chromosome(position_list) 
        # self.IBD_matrix = np.zeros((l, l, self.chrom_l * 10), dtype=np.int_)  # Matrix for IBD status in 0.1 cM steps
    
    def set_random_samples(self, k):
        '''Picks k random samples'''
        position_list = [(i + self.sample_steps / 2, j + self.sample_steps / 2, 0) for i in 
                         range(0, self.gridsize, self.sample_steps) for j in range(0, self.gridsize, self.sample_steps)]
        shuffle(position_list)  # Randomize position List
        self.set_samples(position_list[:k])  # Set the samples
                     
    def set_chromosome(self, positions):  # Initializes Chromosome on the given list of positions (List with entry (pos_x,pos_y,chrom) )
        for i in positions:
            self.update_list.append(i)               
            self.grid[i] = [BlPiece(i, 0, self.chrom_l)]  # Create chromosome block
            self.start_list.append(i)
    
    def add_block(self, position, start, end):
        '''Adds desired block to grid'''
        if self.grid[position] == None:  # In case nothing is there already add an empty list
            self.grid[position] = []
            self.update_list.append(position)
            
        self.grid[position].append(BlPiece(position, start, end))  # Generates and appends desired block piece
        
    def add_block1(self, position, block):
        '''Quickly adds block without recombination event'''    
        if self.grid1[position] == None:  # In case nothing is there already add an empty list
            self.grid1[position] = []
            self.update_list.append(position)  # Write position in update List 
        self.grid1[position].append(block)  # Generates and appends desired block piece
        
        
    def add_block_rec(self, position, block, start, end):
        '''Adds block hit by recombination / More complicated since Multiblocks possible'''
        
        # Check whether block too short
        if self.delete == True:
            if (end - start) < self.IBD_treshold:  # If smaller than IBD_Treshold STOP
                return
        
        if self.grid1[position] == None:  # In case nothing is there already add an empty list
            self.grid1[position] = []
            self.update_list.append(position)  # Write position in update List
        
        if isinstance(block, Multi_Bl):  # If already complicated block
            subblocks = block.sub_blocks  # Extract subblocks
            newblocks = [[max(subblock.start, start), min(subblock.end, end), subblock.origin] for subblock in subblocks]
            newblocks = [block for block in newblocks if (block[1] - block[0]) > (self.delete * self.IBD_treshold)]  # Only positive lengths and above treshold
            red_subblocks = [BlPiece(i[2], i[0], i[1]) for i in newblocks]
            if red_subblocks:  # Only append blocks if they are actually there
                self.grid1[position].append(Multi_Bl(red_subblocks))
                    
        elif isinstance(block, BlPiece):  # Update simple block
            self.grid1[position].append(BlPiece(block.origin, start, end))    
               
    def reset_grid(self):
        '''Method to reset the Grid and delete all blocks.'''
        self.grid = np.empty((self.gridsize, self.gridsize, 2), dtype=np.object)
        self.update_list = []
        self.t = 0
        self.IBD_blocks = []
        self.start_list = []
        
    def update_IBD_blocks_demes(self, deme_size):
        '''Updates the position of IBD-blocks to be in center of the deme-size; and update start list'''
        for i in range(0, len(self.IBD_blocks)):
            origin1 = self.IBD_blocks[i][2]  # Extract coordinates
            origin2 = self.IBD_blocks[i][3]
            origin1 = (self.mean_deme_position(origin1[0], deme_size), self.mean_deme_position(origin1[1], deme_size), origin1[2])  # Modify coordinates accordingly
            origin2 = (self.mean_deme_position(origin2[0], deme_size), self.mean_deme_position(origin2[1], deme_size), origin2[2])                    
            self.IBD_blocks[i] = (self.IBD_blocks[i][0], self.IBD_blocks[i][1], origin1, origin2, self.IBD_blocks[i][4])  # Modify whole entry 
        
        for i in range(0, len(self.start_list)):  # Also update start list
            self.start_list[i] = (self.mean_deme_position(self.start_list[i][0], deme_size), self.mean_deme_position(self.start_list[i][1], deme_size), self.start_list[i][2])         
    
    def create_new_grid(self, nr_inds_pn=2):
        '''Generates an empty grid to fill up with stuff'''
        return np.empty((self.gridsize, self.gridsize, 2 * nr_inds_pn), dtype=np.object)  # Delete Update grid    
                  
    def generation_update(self):  
        '''Updates a single generation'''       
        update_list = self.update_list  # Make working copy of update list
        self.update_list = []  # Delete update list
        
        for position in update_list:
            x, y = position[0], position[1]
            value = self.grid[position]
            
            # In case of a single block send it to updater:    
            if len(value) == 1:  
                self.update_single_block(value[0], (x, y))
             
            # In case of multiple blocks detect IBDs and do whole chromosome break points                   
            elif len(value) >= 2:  
                self.grid[position].sort(key=attrgetter('start'))  # First sort list of blocks according to their start position:
                self.IBD_blocks += self.IBD_search(position)  # Do IBD detection
                self.merge_blocks(position)  # Merge Blocks
                
                rec_points, ancestry = self.create_break_points((x, y))  # Gets random recombination break points and ancestry of blocks
                    
                for block in self.grid[position]:
                    i = bisect.bisect_right(rec_points, block.start)  # The first rec-point greater than start of the block
                    bl_start = block.start  # The first new block
                    if rec_points[i] >= block.end:
                        self.add_block1(ancestry[i], block)
                        continue
                    
                    bl_end = rec_points[i]                        
                        
                    while bl_end < block.end:
                        self.add_block_rec(ancestry[i], block, bl_start, bl_end)  # ancestry[i] is ancestry before breakpoint
                        i += 1
                        bl_start = bl_end
                        bl_end = rec_points[i]
                        
                    self.add_block_rec(ancestry[i], block, bl_start, block.end)  # Do the last block, possibly end of chromosome
                        
        self.grid = self.grid1  # Update the grid
        self.t += 1                              
    
    def get_parents_pos(self, x, y): 
        '''Yield the parental chromosomes given position (x,y)'''
        (x1, y1) = tuple(self.drawer.draw_parent((x, y)))  # Draw first parental position    
        chrom_1 = (random() < 0.5)  # Draw random boolean for first parental chromosome
        chrom_2 = not chrom_1
        pos1 = (x1, y1, chrom_1)
        pos2 = (x1, y1, chrom_2)
        return (pos1, pos2)  # Return the position of the two parental chromosomes
                      
    def update_single_block(self, block, (x, y)):
        '''Updates the given block to its given parental positions'''
        recpoint = block.start  # Save last recombination points
        
        pos1, pos2 = self.get_parents_pos(x, y)  # Get parental positions
        
        r = np.random.exponential(scale=self.rec_rate)  # First rec. point
        if (recpoint + r) >= block.end:  # If only one block
                self.add_block1(pos1, block)
                return  # Finished
        while True:
            self.add_block_rec(pos1, block, recpoint, recpoint + r)  # Add block
            
            recpoint += r  # Update to new start
            r = np.random.exponential(scale=self.rec_rate)  # Next recombination
            if (recpoint + r) >= block.end:  # Break if over limit
                self.add_block_rec(pos2, block, recpoint, block.end)  # Add final block
                return
            self.add_block_rec(pos2, block, recpoint, recpoint + r)  # Add block
            
            recpoint += r  # Update to new start
            r = np.random.exponential(scale=self.rec_rate)  # Next recombination
            if (recpoint + r) >= block.end:  # Break if over limit
                self.add_block_rec(pos1, block, recpoint, block.end)  # Add final block
                return               
    
    def update_t(self, t):
        '''Updates the Grid t generations'''
        start = timer()
        for i in range(0, t):
            print("Doing step: " + str(i))
            self.grid1 = self.create_new_grid()  # Make new empty update grid 
            self.generation_update()
        end = timer()
        print("Time elapsed: %.3f" % (end - start))
        print("IBD Blocks found: " + str(len(self.IBD_blocks)))      
            
            
    def create_break_points(self, (x, y)):
        '''Create a set of breakpoints for the whole chromosome and returns it as list
        Also get according parent position list'''
        rec_point = 0  # The first rec point sits at 0 ofc
        rec_points = [0]
        while True:  # Generate List of breakpoints
            r = np.random.exponential(scale=self.rec_rate)
            rec_point += r
            
            if rec_point < self.chrom_l:
                rec_points.append(rec_point)
            
            else:  # If end reached return full list of recombination points + chromosome ends
                rec_points.append(self.chrom_l)
                break
            
        pos1, pos2 = self.get_parents_pos(x, y)
        n = len(rec_points)
        ancestry = [pos1, pos2] * (n / 2) + [pos1] * (n % 2)  # Create full lenth ancestral pos vector
        return (rec_points, ancestry)
    
    def IBD_search(self, location):
        '''Takes list of blocks and their position at given position as input and returns list of IBD-segments above threshold '''       
        block_list = self.grid[location]
        block_list.sort(key=attrgetter('start'))  # First sort list of blocks according to their start position:
        
        position = 0  # Current search position
        IBD_list = []
        
        # Check for pairwise overlaps:    
        n = len(block_list)  # Access length of blocks to avoid new blocks in loop
        for i in range(0, n):  # Check every possible overlap with this block
            block = block_list[i]
            position = block.end
            for j in range(i + 1, n):  # Check with all higher blocks
                candidate = block_list[j]
                if candidate.start <= position:  # Detect overlap
                    length = (min(position, candidate.end) - candidate.start)
                    if length > self.IBD_treshold:  # Trigger IBD detection procedure
                        IBD_blocks = self.IBD_overlap(block, candidate)  # Get overlaps and all sub-blocks
                        IBD_list += IBD_blocks
                        # candidate.update_length(position - (self.IBD_treshold - 1), candidate.end)  # To avoid late double findings delete overlap for the second block.
                else:
                    break  # Stop search for this block (start of following blocks beyond its end)
        return IBD_list
    
    def merge_blocks(self, location):
        block_list = self.grid[location]
        # Go along chromosome and add new multi-blocks:
        end = block_list[0].end  # First do the first blocks
        subblocks = [block_list[0]]
        merged_blocks = []
        
        for i in block_list[1:]:
            if (i.start > end):  # If gap
                merged_blocks.append(Multi_Bl(subblocks))
                end = i.end
                subblocks = [i]
            else:
                subblocks.append(i)  # Else append to overlapping block list
                
            if i.end > end:  # Extend end if necessary
                end = i.end
        merged_blocks.append(Multi_Bl(subblocks))  # For last block.
        self.grid[location] = merged_blocks  # Set blocks to sorted blocks

    def IBD_overlap(self, block1, block2):
        '''Detects overlap between block1 and block2 (can be multiblocks)'''
        IBD_list = []
        
        # Extract possible subblocks
        bl1, bl2 = [], []
        if isinstance(block1, Multi_Bl):
            bl1 += block1.sub_blocks
        else: bl1.append(block1)
                            
        if isinstance(block2, Multi_Bl):
            bl2 += block2.sub_blocks
        else: bl2.append(block2)
        
        # Check all possible pairs of subblocks
        for b1 in bl1:
            for b2 in bl2:
                end = min(b1.end, b2.end)
                start = max(b1.start, b2.start)
                length = end - start
                if length >= self.IBD_treshold:
                    IBD_list.append((start, length, b1.origin, b2.origin, self.t))           
        return(IBD_list)
            
        
    def mean_deme_position(self, position, deme_size):
        '''Return the middle position of the deme under question. Same as used in deme_drawer'''
        return((deme_size * np.around(position / float(deme_size) + 0.001)) % self.gridsize)  # 8-12->10 
    
    def plot_distribution(self):
        '''Plots the distribution of the Chromosomes on current grid'''      
        x_list, y_list, colors, size = [], [], [], []
        # First extract the data from the last slice
        
        for (x, y, chrom), value in np.ndenumerate(self.grid):  # Iterate over all positions @UnusedVariable
            if value:  # Basically pythonic for if list not empty
                for block in value:
                    if isinstance(block, Multi_Bl):
                        block_list = block.sub_blocks
                    else:   
                        block_list = [block]
                        
                    for block in block_list:
                        x_list.append(x)
                        y_list.append(y)
                        colors.append(20 * block.origin[0] + block.origin[1])
                        size.append(block.end - block.start)
            
        size = [5 * s for s in size]  # Heuristic scale factor
        
        # Now do the plot: (marker="|")
        plt.scatter(x_list, y_list, c=colors, s=size , alpha=0.5)
        plt.xlim([0, self.gridsize - 1])
        plt.ylim([0, self.gridsize - 1])
        plt.title("Generation " + str(self.t))
        # plt.text(1,1,"Generation " + str(self.t))
        plt.show()
        return((x_list, y_list, colors, size))  # Return for possible plots
    
    

#############################################################################
    # Methods to create MLE object#
       
    def create_MLE_object(self, bin_pairs=True):
        '''Return initialized MLE-sharing object'''
        pair_dist, pair_IBD, pair_nr = self.give_lin_IBD(bin_pairs=bin_pairs)  # Get the relevant data
        return MLE_analyse(0, pair_dist, pair_IBD, pair_nr, error_model=False)  # Initialize POPRES-MLE-analysis object
    
    def give_lin_IBD(self, bin_pairs=False):
        '''Method which returns pairwise distance, IBD-sharing and pw. Number.
        Used for full MLE-Method. If bin==True pool same distances. Return arrays'''
        l = len(self.start_list) 
        pair_IBD = np.zeros((l * (l - 1) / 2))  # List of IBD-blocks per pair
        pair_IBD = [[] for _ in pair_IBD]  # Initialize with empty lists
        
        # Iterate over all IBD-blocks
        for bpair in self.IBD_blocks:
            ibd_length = bpair[1]  # Get length in centiMorgan
            ind1 = self.start_list.index(bpair[2])
            ind2 = self.start_list.index(bpair[3])    
            j, i = min(ind1, ind2), max(ind1, ind2) 
            pair_IBD[i * (i - 1) / 2 + j].append(ibd_length)  # Append an IBD-block  
        
        # Get distance Array of all blocks
        pair_dist = [torus_distance(self.start_list[i][0], self.start_list[i][1],
                                    self.start_list[j][0], self.start_list[j][1], self.gridsize) for i in range(0, l) for j in range(0, i)]
        pair_nr = np.ones(len(pair_dist))
        pair_dist, pair_IBD = pair_dist, pair_IBD
        
        if bin_pairs == True:  # Pool data if wanted (speeds up MLE)
            pair_dist, pair_IBD, pair_nr = self.pool_lin_IBD_shr(pair_dist, pair_IBD, pair_nr)
        return (np.array(pair_dist), np.array(pair_IBD), np.array(pair_nr)) 
    
    def pool_lin_IBD_shr(self, pw_dist, pair_IBD, pair_nr):
        '''Bins pairs of same length into one distance pair.
        This does not change the likelihood function but speeds up calculation'''
        distances = sorted(set(pw_dist))  # Produce the keys in a sorted fashion
        
        new_pair_IBD = [[] for _ in distances]  # Initialize the new shortened arrays
        new_pair_nr = [0 for _ in distances]
        
        for j in range(len(distances)):
            r = distances[j]
            for i in range(len(pw_dist)):  # Iterate over all pairs
                if pw_dist[i] == r:  # If Match
                    new_pair_IBD[j] += list(pair_IBD[i])  # Append the shared blocks
                    new_pair_nr[j] += pair_nr[i]  # Add the number of individuals
                    
        print("Nr. of all pairs: %i" % np.sum(new_pair_nr))
        print("Nr of total blocks for analysis: %i" % np.sum([len(i) for i in new_pair_IBD]))
        return(distances, new_pair_IBD, new_pair_nr) 
    
    
#####################################################################################################
class Grid_Grow(Grid):
    '''Class for producing a growing grid'''
    nr_inds_pn = 1  # The Number of chromosomes per node
    
    def __init__(self, **kwds):
        super(Grid_Grow, self).__init__(**kwds)  # Initialize the grid        
    # To Do: Update specific aspects 
    
    def set_chr_pn(self, t_back):
        '''Method to set individuals per node in generation t''' 
        #mu = 200.0 / t_back
        mu = t_back
        #mu = 10  # 10 before change for Hybride Zone Sim (5)
        self.nr_inds_pn = np.around(mu)
        
    def update_t(self, t):
        '''Updates the Grid t generations'''
        start = timer()
        for i in range(0, t):
            print("Doing step: " + str(i))
            self.set_chr_pn(self.t + 1)  # Set Nr of individuals per node t generations back
            self.grid1 = self.create_new_grid(self.nr_inds_pn)  # Make new empty update grid
            self.generation_update()
        end = timer()
        print("Time elapsed: %.3f" % (end - start))
        print("IBD Blocks found: " + str(len(self.IBD_blocks)))  
    
    def get_parents_pos(self, x, y):
        '''Override original method to get parental chromosome position'''
        (x1, y1) = tuple(self.drawer.draw_parent((x, y)))  # Draw first parental position 
        p = 2 * np.random.randint(self.nr_inds_pn)  # Draw parent individual begin chromosome
        chrom_1 = (random() < 0.5)  # Draw random boolean for first parental chromosome
        chrom_2 = not chrom_1
        pos1 = (x1, y1, p + chrom_1)
        pos2 = (x1, y1, p + chrom_2)
        return (pos1, pos2)  # Return the position of the two parental chromosomes   

    
########################################################################################################

def factory_Grid(growing=0):
    '''Factory method to give back Grid'''
    if growing:
        return Grid_Grow()
    else:
        return Grid()

    
    
