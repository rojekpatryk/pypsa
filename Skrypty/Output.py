import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import config as cfg
from InputData import read_input_data, read_costs, read_time_series, read_scenarios_configuration
from Plotting import *
from Extras import Dunkelflaute_analysis
import datetime
import os

class ModelResults():
    def __init__(self, dirname=None, network_scenarios=None):
        print('generating results start: ', datetime.datetime.now())
        start_time = datetime.datetime.now()
        self.dirname = dirname
        self.scenarios_configuration = read_scenarios_configuration()
        self.scenarios_configuration = self.scenarios_configuration.set_index(self.scenarios_configuration['Scenario'])
        self.network_scenarios = network_scenarios

        self.tech_variable_df = pd.read_excel('../InputData/' + cfg.input_excel_name + '.xlsx', sheet_name='tech_variable', index_col=0)

        self.plots_dirname = os.path.join(self.dirname, "Plots")
        os.mkdir(self.plots_dirname)
        for i in [1, 2, 3, 4, 5, 6]:
            os.mkdir(os.path.join(self.plots_dirname, cfg.plot_names_dict['fig ' + str(i)]))

        # Dunkelflaute_analysis(dirname)

        # scenarios_list = self.scenarios_configuration.index.tolist()
        # p_by_generator_results = pd.DataFrame()
        pu_costs_by_year = pd.DataFrame()
        p_onshore_ratio_by_year = pd.DataFrame()
        p_PV_ratio_by_year = pd.DataFrame()
        p_nom_opt_by_year = pd.DataFrame()
        gen_nom_opt_by_year = pd.DataFrame()
        cf_by_year = pd.DataFrame()
        cf_p_nom_max_by_year = pd.DataFrame()
        cost_of_energy_by_year = pd.DataFrame()
        objective_components_by_year = pd.DataFrame()

        for key in self.network_scenarios:
            year = int(key.split('_')[0])
            scenario = key.split('_')[1]
            n = self.network_scenarios[key]
            print('\n----------POSTPROCESSING Scenariusz: ', scenario, ', Rok: ', year,
                  ' ------------------------------')
            print('-------------------------- Czas obliczeń: ', datetime.datetime.now() - start_time,
                  ' ---------------------------\n')

            if hasattr(n, 'objective'):
                # p_by_generator_results = self.p_by_generator(n, scenario, year, p_by_generator_results)
                pu_costs_by_year = self.pu_costs(n, scenario, year, pu_costs_by_year)
                p_onshore_ratio_by_year, p_PV_ratio_by_year = self.p_RES_ratio(n, scenario, year, p_onshore_ratio_by_year, p_PV_ratio_by_year)
                p_nom_opt_by_year = self.p_nom_opt_values(n, scenario, year, p_nom_opt_by_year)
                gen_nom_opt_by_year = self.gen_nom_opt_values(n, scenario, year, gen_nom_opt_by_year)
                cf_by_year = self.cf_by_years_values(n, scenario, year, cf_by_year)
                cf_p_nom_max_by_year = self.cf_p_nom_max_by_years_values(n, scenario, year, cf_p_nom_max_by_year)
                cost_of_energy_by_year = self.yearly_cost_of_energy(n, scenario, year, cost_of_energy_by_year)
                objective_components_by_year = self.get_objective_components(n, scenario, year, objective_components_by_year)
                self.generate_plots(n, scenario, year)

        sheetnames_list = ['pu_costs_by_year',
                           'p_onshore_ratio_by_year',
                           'p_PV_ratio_by_year',
                           'p_nom_opt_by_year',
                           'gen_nom_opt_by_year',
                           'cf_by_year',
                           'cf_p_nom_max_by_year',
                           'cost_of_energy_by_year',
                           'objective_components_by_year']
        # first_col = p_nom_opt_by_year.pop('scenario')
        # sec_col = p_nom_opt_by_year.pop('year')
        # p_nom_opt_by_year.insert(0, 'scenario', first_col)
        # p_nom_opt_by_year.insert(1, 'year', sec_col)
        for df in [p_nom_opt_by_year, gen_nom_opt_by_year, objective_components_by_year, cf_by_year, cf_p_nom_max_by_year, cost_of_energy_by_year]:
            df = self.p_gen_table_order(df)
        # p_nom_opt_by_year = self.P_Gen_table_order(p_nom_opt_by_year)
        # gen_nom_opt_by_year = self.P_Gen_table_order(gen_nom_opt_by_year)
        # objective_components_by_year = self.P_Gen_table_order(objective_components_by_year)
        pu_costs_by_year = pu_costs_by_year.reindex(sorted(pu_costs_by_year.columns), axis=1)
        p_onshore_ratio_by_year = p_onshore_ratio_by_year.reindex(sorted(p_onshore_ratio_by_year.columns), axis=1)
        p_PV_ratio_by_year = p_PV_ratio_by_year.reindex(sorted(p_PV_ratio_by_year.columns), axis=1)
        p_nom_opt_by_year = p_nom_opt_by_year.sort_values(by=['scenario', 'year'], ascending=[True, True], na_position='last')
        gen_nom_opt_by_year = gen_nom_opt_by_year.sort_values(by=['scenario', 'year'], ascending=[True, True], na_position='last')
        cf_by_year = cf_by_year.sort_values(by=['scenario', 'year'], ascending=[True, True], na_position='last')
        cf_p_nom_max_by_year = cf_p_nom_max_by_year.sort_values(by=['scenario', 'year'], ascending=[True, True], na_position='last')
        cost_of_energy_by_year = cost_of_energy_by_year.sort_values(by=['scenario', 'year'], ascending=[True, True], na_position='last')
        objective_components_by_year = objective_components_by_year.sort_values(by=['scenario', 'year', 'cost type'], ascending=[True, True, True], na_position='last')

        self.save_excel_results([pu_costs_by_year,
                                 p_onshore_ratio_by_year,
                                 p_PV_ratio_by_year,
                                 p_nom_opt_by_year,
                                 gen_nom_opt_by_year,
                                 cf_by_year,
                                 cf_p_nom_max_by_year,
                                 cost_of_energy_by_year,
                                 objective_components_by_year], sheetnames_list)
        print('saving hourly results: ', datetime.datetime.now())
        self.save_hourly_results()
        print('generating results end: ', datetime.datetime.now())
        pass

    def p_by_generator(self, n, scenario, year, df):
        p_by_generator_df = n.generators_t.p

        if not n.storage_units.empty:
            sto = n.storage_units_t.p.T.groupby(n.storage_units.carrier).sum().T
            p_by_generator_df = pd.concat([p_by_generator_df, sto], axis=1)

        p_by_generator_df = p_by_generator_df.sum(axis=0) #TODO double check

        p_by_generator_df['scenario'] = scenario
        p_by_generator_df['year'] = year

        return pd.concat([df, p_by_generator_df], ignore_index=True) #df.append(p_by_generator_df)

    def pu_costs(self, n, scenario, year, df):
        if cfg.ENS_adjustment:
            gen_marginal_costs = n.generators.marginal_cost
            if 'ENS' in list(gen_marginal_costs.index):
                gen_marginal_costs.at['ENS'] = self.tech_variable_df.at['ENS_adjustment', year]
        else:
            gen_marginal_costs = n.generators.marginal_cost
        capex_components = (n.generators.capital_cost * n.generators.p_nom_opt)._append(
            n.storage_units.p_nom_opt * n.storage_units.capital_cost)
        opex_components = (gen_marginal_costs * n.generators_t.p).sum()  # PYPSA na koszty zmienne też mówi OPEX

        assert np.abs((opex_components.sum() - n.statistics.opex().sum())) < 0.1
        assert np.abs((capex_components.sum() - n.statistics.capex().sum())) < 0.1
        # Calculate total costs and per-unit costs
        total_costs = capex_components.sum() + opex_components.sum()
        pu_costs = total_costs / (n.loads_t.p_set.sum() * cfg.resolution)
        df.loc[scenario, year] = pu_costs.iloc[0]
        return df

    def p_RES_ratio(self, n, scenario, year, p_onshore_ratio_by_year, p_PV_ratio_by_year):
        p_nom_opt_PV = n.generators.p_nom_opt['solar']
        p_nom_opt_onshore = n.generators.p_nom_opt['onwind']
        p_nom_max_PV = n.generators.p_nom_max['solar']
        p_nom_max_onshore = n.generators.p_nom_max['onwind']
        p_PV_ratio_by_year.loc[scenario, year] = p_nom_opt_PV/p_nom_max_PV
        p_onshore_ratio_by_year.loc[scenario, year] = p_nom_opt_onshore/p_nom_max_onshore
        return p_onshore_ratio_by_year, p_PV_ratio_by_year

    def p_nom_opt_values(self, n, scenario, year, p_nom_opt_by_year):
        df = pd.DataFrame(n.generators.p_nom_opt).T
        for storage_name, storage_p_nom_opt in n.storage_units.p_nom_opt.items():
            df[storage_name] = storage_p_nom_opt
        df['scenario'] = scenario
        df['year'] = year
        p_nom_opt_by_year = pd.concat([p_nom_opt_by_year, df])

        return p_nom_opt_by_year

    def gen_nom_opt_values(self, n, scenario, year, gen_nom_opt_by_year):
        df = pd.DataFrame(n.generators_t.p.sum()).T
        for storage_name in n.storage_units_t.p:
            discharge_mask = n.storage_units_t.p[storage_name] > 0
            charge_mask = n.storage_units_t.p[storage_name] < 0
            storage_generation = n.storage_units_t.p[discharge_mask].sum().loc[storage_name]
            storage_charging = n.storage_units_t.p[charge_mask].sum().loc[storage_name]
            df[storage_name + '_discharge'] = storage_generation
            df[storage_name + '_charge'] = storage_charging
        df['scenario'] = scenario
        df['year'] = year
        gen_nom_opt_by_year = pd.concat([gen_nom_opt_by_year, df])

        return gen_nom_opt_by_year

    def cf_by_years_values(self, n, scenario, year, cf_by_year):
        pu_df = pd.DataFrame(n.generators.p_nom_opt).T
        for storage_name, storage_p_nom_opt in n.storage_units.p_nom_opt.items():
            pu_df[storage_name] = storage_p_nom_opt
        pu_df = pu_df.reset_index(drop=True)

        gen_df = pd.DataFrame(n.generators_t.p.sum()).T
        for storage_name in n.storage_units_t.p:
            # discharge_mask = n.storage_units_t.p[storage_name] > 0
            charge_mask = n.storage_units_t.p[storage_name] < 0
            # storage_generation = n.storage_units_t.p[discharge_mask].sum().loc[storage_name]
            storage_charging = n.storage_units_t.p[charge_mask].sum().loc[storage_name]
            # df[storage_name + '_discharge'] = storage_generation
            gen_df[storage_name] = storage_charging
        gen_df = gen_df.reset_index(drop=True)

        df = gen_df / (pu_df * 8760)

        # if 'CCGT new' in df.columns:
        #     df['CCGT new'] = df['CCGT new'] * 4

        df['scenario'] = scenario
        df['year'] = year
        cf_by_year = pd.concat([cf_by_year, df])
        return cf_by_year

    def cf_p_nom_max_by_years_values(self, n, scenario, year, cf_by_year):
        pu_df = pd.DataFrame(n.generators.p_nom_max).T
        for storage_name, storage_p_nom_max in n.storage_units.p_nom_max.items():
            pu_df[storage_name] = storage_p_nom_max
        pu_df = pu_df.reset_index(drop=True)

        gen_df = pd.DataFrame(n.generators_t.p.sum()).T
        for storage_name in n.storage_units_t.p:
            # discharge_mask = n.storage_units_t.p[storage_name] > 0
            charge_mask = n.storage_units_t.p[storage_name] < 0
            # storage_generation = n.storage_units_t.p[discharge_mask].sum().loc[storage_name]
            storage_charging = n.storage_units_t.p[charge_mask].sum().loc[storage_name]
            # df[storage_name + '_discharge'] = storage_generation
            gen_df[storage_name] = storage_charging
        gen_df = gen_df.reset_index(drop=True)

        df = gen_df / (pu_df * 8760)

        # if 'CCGT new' in df.columns:
        #     df['CCGT new'] = df['CCGT new'] * 4

        df['scenario'] = scenario
        df['year'] = year
        cf_by_year = pd.concat([cf_by_year, df])
        return cf_by_year

    def yearly_cost_of_energy(self, n, scenario, year, cost_of_energy_by_year):
        capex_components = pd.DataFrame((n.generators.capital_cost * n.generators.p_nom_opt)._append(
            n.storage_units.p_nom_opt * n.storage_units.capital_cost)).T
        capex_components = capex_components.reset_index(drop=True)
        opex_components = pd.DataFrame((n.generators.marginal_cost * n.generators_t.p).sum()).T
        opex_components = opex_components.reset_index(drop=True)

        # pu_df = pd.DataFrame(n.generators.p_nom_opt).T
        # for storage_name, storage_p_nom_opt in n.storage_units.p_nom_opt.items():
        #     pu_df[storage_name] = storage_p_nom_opt
        # pu_df = pu_df.reset_index(drop=True)
        gen_df = pd.DataFrame(n.generators_t.p.sum()).T
        for storage_name in n.storage_units_t.p:
            discharge_mask = n.storage_units_t.p[storage_name] > 0
            # charge_mask = n.storage_units_t.p[storage_name] < 0
            storage_generation = n.storage_units_t.p[discharge_mask].sum().loc[storage_name]
            # storage_charging = n.storage_units_t.p[charge_mask].sum().loc[storage_name]
            # df[storage_name + '_discharge'] = storage_generation
            gen_df[storage_name] = storage_generation
        gen_df = gen_df.reset_index(drop=True)

        cost_of_energy_df = (capex_components + opex_components)/gen_df

        cost_of_energy_df['scenario'] = scenario
        cost_of_energy_df['year'] = year
        cost_of_energy_by_year = pd.concat([cost_of_energy_by_year, cost_of_energy_df])
        return cost_of_energy_by_year

    def get_objective_components(self, n, scenario, year, objective_components_by_year):
        capex_components = pd.DataFrame((n.generators.capital_cost * n.generators.p_nom_opt)._append(n.storage_units.p_nom_opt * n.storage_units.capital_cost)).T
        opex_components = pd.DataFrame((n.generators.marginal_cost * n.generators_t.p).sum()).T  # PYPSA na koszty zmienne też mówi OPEX
        capex_components['cost type'] = 'CAPEX'
        opex_components['cost type'] = 'Var Costs'

        capex_components['scenario'] = scenario
        capex_components['year'] = year
        opex_components['scenario'] = scenario
        opex_components['year'] = year
        objective_components_by_year = pd.concat([objective_components_by_year, capex_components, opex_components])

        return objective_components_by_year

    def generate_plots(self, n, scenario, year):
        plt.style.use("ggplot")
        generators_list = self.scenarios_configuration.loc[scenario, 'Generators'].replace('"', '').split(', ')
        BASE_load_name = self.scenarios_configuration.loc[scenario, 'BASE_load_name']
        mix, commodities, base_load, renewables, tech_sheet, tech_variable = read_input_data(year, BASE_load_name)
        costs = read_costs(year, tech_sheet, tech_variable, commodities)

        n.generators_t.p_max_pu.dropna(axis=0).plot( ylabel="CF")
        n.loads_t.p_set.plot(ylabel="MW")

        plot_dispatch(n, year, generators_list)
        plot_costs_twin_y_axis_with_storage(n, costs, year)
        plot_objective_components(n, year)
        plot_capacity_and_generation(n, year)

        fig_nums = plt.get_fignums()
        figs = [plt.figure(n) for n in fig_nums]
        for fig in figs:
            plt.gcf().set_size_inches(12,9)
            fig.savefig(os.path.join(self.plots_dirname, cfg.plot_names_dict['fig ' + str(fig.number)], scenario + '_' + str(year) + ' ' + cfg.plot_names_dict['fig ' + str(fig.number)] + '.png'),
            # fig.savefig(os.path.join(self.plots_dirname, 'fig '+str(fig.number) + cfg.plot_names_dict['fig '+str(fig.number)], scenario+'_'+cfg.plot_names_dict['fig '+str(fig.number)]+'.png'),
                        dpi = 300)
            plt.close()

    def p_gen_table_order(self, df):
        first_col = df.pop('scenario')
        sec_col = df.pop('year')
        df.insert(0, 'scenario', first_col)
        df.insert(1, 'year', sec_col)
        return df

    def save_excel_results(self, dataframes_list, sheetnames_list):
        with pd.ExcelWriter(os.path.join(self.dirname, "results_" + datetime.datetime.now().strftime("%d_%m_%Y_%H_%M") + ".xlsx")) as writer:
            for i, df in enumerate(dataframes_list):
                df.to_excel(writer, sheet_name=sheetnames_list[i])

    def save_hourly_results(self):
        # scenarios_list = self.scenarios_configuration.index.tolist()
        with pd.ExcelWriter(os.path.join(self.dirname, "hourly_results_" + datetime.datetime.now().strftime("%d_%m_%Y_%H_%M") + ".xlsx")) as writer:
            for key in self.network_scenarios:
                n = self.network_scenarios[key]
                year = key.split('_')[0]
                scenario = key.split('_')[1]
                if hasattr(n, 'objective'):
                    df = pd.concat([n.generators_t.p, n.storage_units_t.p, n.loads_t.p], axis=1)
                    df.to_excel(writer, sheet_name=scenario+'_'+str(year))
