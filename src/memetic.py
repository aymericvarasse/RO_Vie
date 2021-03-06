# The four stages are:
#   - initial population generation
#   - solution crossing
#   - mutation
#   - local search
#   - selection
# The 3 last stages are iterated several times

import time
from src import initial_population, mutation, local_search, solution_crossover, population_statistics
from src.convergence import is_convergent, initialize_threshold


def update_population(population, flowshop, parameters, swap_neighbors, insert_neighbors):
    """
    update_population function called when building a new generation of population
    :param population: population to update
    :param flowshop: instance of the flowshop problem
    :param parameters: dictionary of parameters used in the function
    :param swap_neighbors: the list of neighbors for the swap method
    :param insert_neighbors: the list of neighbors for the insert method
    :return: the updated population
    """
    population = solution_crossover.crossover(flowshop,
                                              population,
                                              cross_1_point_prob=parameters['cross_1_point_prob'],
                                              cross_2_points_prob=parameters['cross_2_points_prob'],
                                              cross_position_prob=parameters['cross_position_prob'],
                                              gentrification=parameters['gentrification'])
    population = mutation.mutation(flowshop,
                                   population,
                                   mutation_swap_probability=parameters['mut_swap_prob'],
                                   mutation_insert_probability=parameters['mut_insert_prob'])
    if parameters['use_ls']:
        population = local_search.local_search(population,
                                               maximum_nb_iterations=parameters['ls_max_iterations'],
                                               local_search_swap_prob=parameters['ls_swap_prob'],
                                               local_search_insert_prob=parameters['ls_insert_prob'],
                                               max_neighbors_nb=parameters['max_neighbors_nb'],
                                               swap_neighbors=swap_neighbors,
                                               insert_neighbors=insert_neighbors,
                                               nb_sched=parameters['ls_subset_size'])
    return population


def restart_population(population, flowshop, preserved_prop):
    """
    restart_population function called when the population is convergent
    :param population: population to restart
    :param flowshop: instance of the flowshop problem
    :param preserved_prop: proportion to preserve
    :return: the new population
    """
    preserved_size = int(len(population) * preserved_prop)
    random_size = len(population) - preserved_size
    return (extract_best_from_population(population, preserved_size) +
            initial_population.random_initial_pop(flowshop, random_size))


def extract_best_from_population(population, preserved_size):
    """
    Extracts the preserved_prop proportion of the list list_sched that has the lowest durations
    :param population: list of Ordonnancement objects
    :param preserved_size: number of schedulings to extract from the population
    :return: the list of schedulings (Ordonnancement objects) with the lowest durations of the given size
    """
    sorted_list = sorted(population, key=lambda sched: sched.duree(), reverse=False)
    return sorted_list[:preserved_size]


def memetic_heuristic(flowshop, parameters):
    """
        memetic heuristic for the flowshop problem
        :param flowshop: instance of flowshop
        :param parameters: dict of parameters used in the function.
            It must contain the following keys: 'random_prop', 'deter_prop', 'best_deter', 'pop_init_size',
            'time_limit', 'cross_1_point_prob', 'cross_2_points_prob','cross_position_prob', 'gentrification',
            'mut_swap_prob', 'mut_insert_prob', 'preserved_prop', 'ls_max_iterations', 'ls_swap_prob', 'ls_insert_prob',
            'max_neighbors_nb', 'use_ls', 'ls_subset_size'
        :return: the statistics (mean, min, max) over the generations of the function memetic_heuristic, the scheduling
        (Ordonnancement object) with the lowest duration, the list of iterations where a restart happened
        """
    start_time = time.time()
    swap_neighbors = local_search.create_swap_neighbors(flowshop)
    insert_neighbors = local_search.create_insert_neighbors(flowshop)
    entropy_threshold = initialize_threshold(parameters['pop_init_size'])
    population = initial_population.initial_pop(flowshop,
                                                random_prop=parameters['random_prop'],
                                                deter_prop=parameters['deter_prop'],
                                                best_deter=parameters['best_deter'],
                                                pop_init_size=parameters['pop_init_size'])
    initial_statistics = population_statistics.population_statistics(population)
    list_statistics = [initial_statistics]
    overall_best_scheduling = min(population, key=lambda sched: sched.duree())
    iterations_where_restart = []
    index = 0
    iteration_time = 0
    while time.time() - start_time + iteration_time + 1 < 60 * parameters['time_limit']:
        index += 1
        start_time_iteration = time.time()
        population = update_population(population, flowshop, parameters, swap_neighbors, insert_neighbors)
        best_sched = min(population, key=lambda sched: sched.duree())

        if overall_best_scheduling.duree() > best_sched.duree():
            overall_best_scheduling = best_sched
        statistics = population_statistics.population_statistics(population)
        list_statistics.append(statistics)

        restart = False
        # if the best duration doesn't improve much over 10 iterations, the population is restarted
        if len(list_statistics) > 9 and (iterations_where_restart == [] or index >= iterations_where_restart[-1] + 10) \
                and min([list_statistics[k][1] for k in range(max(0, len(list_statistics)-10), len(list_statistics))]) \
                == max([list_statistics[k][1] for k in range(max(0, len(list_statistics)-10), len(list_statistics))]):
            restart = True

        if is_convergent(population, threshold=entropy_threshold) or restart:
            iterations_where_restart.append(index)
            population = restart_population(population,
                                            flowshop,
                                            preserved_prop=parameters['preserved_prop'])
        iteration_time = time.time() - start_time_iteration
    return list_statistics, overall_best_scheduling, iterations_where_restart
