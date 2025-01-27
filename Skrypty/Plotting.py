import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import config as cfg
from Skrypty.config import ESP_old_capital_cost

figsize = (12, 6)

# Get color dictionary for technologies
color_dict = cfg.color_dict_def

def plot_dispatch(n, year, generators_list):
    p_by_generator = n.generators_t.p

    if cfg.ENS_adjustment:
        if 'ENS' in list(p_by_generator.index):
            p_by_generator.index = p_by_generator.index.str.replace('ENS', cfg.ENS_adjustment_name)

    if not n.storage_units.empty:
        sto = n.storage_units_t.p.T.groupby(n.storage_units.carrier).sum().T
        p_by_generator = pd.concat([p_by_generator, sto], axis=1)

    fig, ax = plt.subplots(figsize=figsize)
    fig.suptitle('Optimized dispatch %i' % year)

    pre_order = list(color_dict.keys())
    order = list(set(pre_order) & set(generators_list)) #część wspólna dwóch list
    color = p_by_generator[order].columns.map(color_dict)

    p_by_generator[order].where(p_by_generator > 0).plot.area(
        ax=ax,
        linewidth=0,
        color=color,
    )

    charge = p_by_generator.where(p_by_generator < 0).dropna(how="all", axis=1)

    if len(charge.min()) == 0:  # todo sprawdzić warunek na charge bo wywala warning że do inputu dajemy te same wartości
        ax.set_ylim(0, n.loads_t.p_set.sum(axis=1).max() * 1.1)
    else:
        ax.set_ylim((charge.min() * 1.1).values[0], n.loads_t.p_set.sum(axis=1).max() * 1.1)

    if not charge.empty:
        charge.plot.area(
            ax=ax,
            linewidth=0,
            color=charge.columns.map(color_dict),
        )

    n.loads_t.p_set.sum(axis=1).plot(ax=ax, c="k")

    plt.legend()
    ax.set_ylabel("MW")
    # if len(charge.min()) == 0:  #todo sprawdzić warunek na charge bo wywala warning że do inputu dajemy te same wartości
    #     ax.set_ylim(0, n.loads_t.p_set.sum(axis=1).max() * 1.1)
    # else:
    #     ax.set_ylim((charge.min() * 1.1).values[0], n.loads_t.p_set.sum(axis=1).max() * 1.1)
    ax.grid(False)

def plot_costs_twin_y_axis_with_storage(n, costs, year):
    """
    Plots a twin y-axis bar plot with generator names on the x-axis, where one y-axis represents
    capital costs and the other y-axis represents marginal costs. Includes storage units with only
    capital costs.

    Parameters:
    n (pypsa.Network): The PyPSA network object.
    costs (pd.DataFrame): DataFrame containing the costs data with generator names as index.

    Returns:
    None
    """
    # Extract generator and storage names
    generator_names = n.generators.index
    storage_names = n.storage_units.index

    # Extract marginal and capital costs for the generators
    marginal_costs = costs.loc[generator_names, 'marginal_cost']
    capital_costs = costs.loc[generator_names, 'capital_cost']

    # Extract costs for storage units
    storage_marginal_costs = pd.Series(0, index=storage_names)
    storage_capital_costs = pd.Series(index=storage_names)

    # BESS_capital_costs = costs.at["battery inverter", "capital_cost"] + cfg.battery_capacity * costs.at["battery storage", "capital_cost"]
    # ESP_old_capital_costs = cfg.ESP_old_capital_cost
    # ESP_new_capital_costs = costs.at["ESP new", "capital_cost"]
    for storage_name in list(storage_names):
        match storage_name:
            case 'battery storage':
                storage_capital_costs[storage_name] = costs.at["battery inverter", "capital_cost"] + cfg.battery_capacity * costs.at["battery storage", "capital_cost"]
            case 'ESP old':
                storage_capital_costs[storage_name] = cfg.ESP_old_capital_cost
            case 'ESP new':
                storage_capital_costs[storage_name] = costs.at["ESP new", "capital_cost"]

    if cfg.ENS_adjustment:
        tech_variable_df = pd.read_excel('../InputData/' + cfg.input_excel_name + '.xlsx',
                                         sheet_name='tech_variable', index_col=0)
        if 'ENS' in list(generator_names):
            marginal_costs.loc['ENS'] = tech_variable_df.loc['ENS_adjustment', year]
            generator_names = generator_names.str.replace('ENS', cfg.ENS_adjustment_name)
            marginal_costs.index = marginal_costs.index.str.replace('ENS', cfg.ENS_adjustment_name)
        if 'ENS' in list(capital_costs.index):
            capital_costs.index = capital_costs.index.str.replace('ENS', cfg.ENS_adjustment_name)

            # Combine generator and storage data
    all_names = generator_names.append(storage_names) #(pd.Series(index=['battery inverter + %ix storage'%cfg.battery_capacity]).index)
    all_capital_costs = capital_costs._append(pd.Series(index=storage_names, data=storage_capital_costs)).div(1e3).round(0)
    all_marginal_costs = pd.concat([marginal_costs, storage_marginal_costs]).round(0)

    # Set up the figure and axis
    fig, ax1 = plt.subplots(figsize=figsize)

    # Set the positions and width for the bars
    bar_width = 0.35
    index = np.arange(len(all_names))

    # Plot the capital costs on the primary y-axis
    colors = all_marginal_costs.index.map(color_dict)

    bars1 = ax1.bar(index, all_capital_costs, bar_width, label='Capital Costs', color=colors, edgecolor='darkgrey', hatch='/')
    ax1.set_xlabel('Generators and Storage Units')
    ax1.set_ylabel('Capital Costs (EUR/MW)', color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')

    # Create a secondary y-axis for the marginal costs
    ax2 = ax1.twinx()
    colors = all_marginal_costs.index.map(color_dict)
    bars2 = ax2.bar(index + bar_width + 0.05, all_marginal_costs, bar_width, label='Marginal Costs', color=colors, edgecolor='darkgrey')
    ax2.set_ylabel('Marginal Costs (EUR/MWh)', color='tab:red')
    ax2.tick_params(axis='y', labelcolor='tab:red')

    # Add labels, title, and legend
    ax1.set_title('Marginal and Capital Costs %i' % year)
    ax1.set_xticks(index + bar_width / 2 + 0.025)
    ax1.set_xticklabels(all_names, rotation=45, ha='right')

    # Add value labels on top of the bars
    def add_labels(bars, ax, unit, color):
        for bar in bars:
            height = bar.get_height()
            ax.annotate('%.0f %s' % (height, unit),
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom',
                        color=color)

    add_labels(bars1, ax1, '\nkEUR/MW/y', 'tab:blue')
    add_labels(bars2, ax2, '\nEUR/MWh', 'tab:red')

    # Remove gridlines
    ax1.grid(False)
    ax2.grid(False)

def plot_objective_components(n, year):
    """
    Plots the components of the objective value resulting from the optimization as a stacked bar plot.

    Parameters:
    n (pypsa.Network): The PyPSA network object.
    year (int): The year for which the plot is being generated.

    Returns:
    None
    """
    # Extract individual CAPEX and OPEX components

    if cfg.ENS_adjustment:
        tech_variable_df = pd.read_excel('../InputData/' + cfg.input_excel_name + '.xlsx',
                                              sheet_name='tech_variable', index_col=0)
        gen_marginal_costs = n.generators.marginal_cost
        if 'ENS' in list(gen_marginal_costs.index):
            gen_marginal_costs.at['ENS'] = tech_variable_df.at['ENS_adjustment', year]
    else:
        gen_marginal_costs = n.generators.marginal_cost

    capex_components = (n.generators.capital_cost * n.generators.p_nom_opt)._append(n.storage_units.p_nom_opt * n.storage_units.capital_cost)
    opex_components = (gen_marginal_costs * n.generators_t.p).sum()

    assert np.abs((opex_components.sum() -  n.statistics.opex().sum())) < 0.1
    assert np.abs((capex_components.sum() -  n.statistics.capex().sum())) < 0.1
    # Calculate total costs and per-unit costs
    total_costs = capex_components.sum() + opex_components.sum()
    pu_costs = total_costs / (n.loads_t.p_set.sum()*cfg.resolution)

    # Create a stacked bar plot
    fig, ax = plt.subplots(figsize=figsize)
    fig.suptitle('Total BASE_%i costs: %.0f blnEUR\n Per-unit costs: %.1f EUR/MWh' % (year, total_costs / 1e9, pu_costs.iloc[0]))

    # Set the positions and width for the bars
    bar_width = 0.35
    index = np.arange(2)  # Two bars: one for CAPEX and one for OPEX

    capex_components = capex_components.div(1e6).round(1)
    opex_components = opex_components.div(1e6).round(1)# PYPSA na koszty zmienne też mówi OPEX

    if cfg.ENS_adjustment:
        if 'ENS' in list(capex_components.index):
            capex_components.index = capex_components.index.str.replace('ENS', cfg.ENS_adjustment_name)
        if 'ENS' in list(opex_components.index):
            opex_components.index = opex_components.index.str.replace('ENS', cfg.ENS_adjustment_name)

    # Plot the stacked bars for CAPEX
    bottom = np.zeros(1)
    for tech in capex_components.index:
        capex = capex_components.loc[tech]
        if capex > 0:
            ax.bar(index[0], capex, bar_width, bottom=bottom, color=color_dict[tech], label=tech, edgecolor='darkgrey')
            bottom += capex

    # Plot the stacked bars for OPEX (koszty zmienne w języku pypsa)
    bottom = np.zeros(1)
    for tech in opex_components.index:
        opex = opex_components.loc[tech]
        if opex > 0:
            if tech in list(capex_components.index):
                ax.bar(index[1], opex, bar_width, bottom=bottom, color=color_dict[tech], edgecolor='darkgrey')
            else:
                ax.bar(index[1], opex, bar_width, bottom=bottom, color=color_dict[tech], label=tech, edgecolor='darkgrey')
            bottom += opex

    # Add labels, title, and legend
    ax.set_xlabel('Fixed & Variable costs of producing BASE_%i'%year)
    ax.set_ylabel('Costs (mEUR)')
    ax.set_title('Costs of delivering BASE_%i with capacity: %.0f MW/h' % (year, n.loads_t.p_set.sum().iloc[0] / 8760))
    ax.set_xticks(index)
    ax.set_xticklabels(['CAPEX', 'Var Costs'])

    # Add value labels on top of the bars
    def add_labels(ax, components, index):
        bottom = np.zeros(1)
        for component in components.index:
            values = components.loc[component]
            height = bottom + values / 2
            ax.annotate('%.0f' % values,
                        xy=(index, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')
            bottom += values

    add_labels(ax, capex_components[capex_components>0], index[0])
    add_labels(ax, opex_components[opex_components >0], index[1])

    # Adjust layout to make room for the x-axis labels
    fig.tight_layout()
    if n.loads_t.p_set.demand.mean() > 1000:
        ax.set_ylim(0, 17000.0)
    else:
        ax.set_ylim(0, 1000.0)

    # Remove gridlines
    ax.grid(False)

    # Add legend
    ax.legend()

def plot_capacity_and_generation(n, year):
    """
    Plots the installed capacity and generation of each generator and storage unit.
    Uses a twin y-axis plot with capacities on one axis and generation on another axis.

    Parameters:
    n (pypsa.Network): The PyPSA network object.
    year (int): The year for which the plot is being generated.

    Returns:
    None
    """
    # Extract generator names and storage names
    generator_names = n.generators.index
    storage_names = n.storage_units.index

    # Extract installed capacities for generators and storage units
    generator_capacities = n.generators.p_nom_opt
    storage_capacities = n.storage_units.p_nom_opt

    # Extract generation for generators and storage units
    generator_generation = n.generators_t.p.sum()
    discharge_mask = n.storage_units_t.p > 0
    storage_generation = n.storage_units_t.p[discharge_mask].sum()

    # Combine generator and storage data
    all_names = generator_names.append(storage_names)
    all_capacities = pd.concat([generator_capacities, storage_capacities]).div(1000).round(1)
    all_generation = pd.concat([generator_generation, storage_generation]).div(1e6).round(1)

    if cfg.ENS_adjustment:
        if 'ENS' in list(all_names):
            all_generation.drop('ENS', inplace=True)
            all_capacities.drop('ENS', inplace=True)
            generator_capacities.drop('ENS', inplace=True)
            generator_names = n.generators.drop('ENS').index
            all_names = generator_names.append(storage_names)


    # Set up the figure and axis
    fig, ax1 = plt.subplots(figsize=figsize)

    # Set the positions and width for the bars
    bar_width = 0.35
    index = np.arange(len(all_names))

    # Plot the installed capacities on the primary y-axis
    colors = all_capacities.index.map(color_dict)

    bars1 = ax1.bar(index, all_capacities, bar_width, label='Installed Capacity (GW)', color=colors, edgecolor='darkgrey', hatch='/')
    ax1.set_xlabel('Generators and Storage Units')
    ax1.set_ylabel('Installed Capacity (GW)', color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')

    # Create a secondary y-axis for the generation
    ax2 = ax1.twinx()
    colors = all_generation.index.map(color_dict)

    bars2 = ax2.bar(index + bar_width + 0.05, all_generation, bar_width, label='Generation (TWh)', color=colors, edgecolor='darkgrey')
    ax2.set_ylabel('Generation (TWh)', color='tab:red')
    ax2.tick_params(axis='y', labelcolor='tab:red')

    # Add labels, title, and legend
    ax1.set_title('Installed Capacity and Generation %i' % year)
    ax1.set_xticks(index + bar_width / 2 + 0.025)
    ax1.set_xticklabels(all_names, rotation=45, ha='right')

    # ax1.set_ylim([0, 1.5])
    # ax2.set_ylim([0, 2.25])

    # Add value labels on top of the bars
    def add_labels(bars, ax, unit, color):
        for bar in bars:
            height = bar.get_height()
            ax.annotate('%.1f %s' % (height, unit),
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', color=color)

    add_labels(bars1, ax1, 'GW', 'tab:blue')
    add_labels(bars2, ax2, 'TWh', 'tab:red')

    # Adjust layout to make room for the x-axis labels
    fig.tight_layout()

    # Remove gridlines
    ax1.grid(False)
    ax2.grid(False)

