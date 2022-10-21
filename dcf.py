import pandas as pd
import yfinance as yf

class DCF:
 
    def __init__(self, symbol, period, rev_growth_rate, tgr):
        self._symbol = symbol
        self._period = period
        self._rev_growth_rate = rev_growth_rate
        self._tgr = tgr
        self._tckr = yf.Ticker(symbol)
        self._info = pd.DataFrame.from_dict(self._tckr.info, orient='index', columns=['Value'])
        # reverse cols (to ascending FYE)
        self._financials = self._tckr.financials[self._tckr.financials.columns[::-1]]
        self._balance_sheet = self._tckr.balance_sheet[self._tckr.balance_sheet.columns[::-1]]
        self._cash_flow = self._tckr.cashflow[self._tckr.cashflow.columns[::-1]]
        # rounds all figures to 2 decimal places
        pd.set_option('display.float_format', lambda x: '%.2f' % x)

    @property
    def symbol(self):
        return self._symbol
    
    @property
    def period(self):
        return self._period
    @period.setter
    def period(self, new_period):
        self._period = new_period

    @property
    def rev_growth_rate(self):
        return self._rev_growth_rate
    @rev_growth_rate.setter
    def rev_growth_rate(self, new_rate):
        self._rev_growth_rate = new_rate
    
    @property
    def tax_rate(self):
        return tax_rate
    @tax_rate.setter
    def tax_rate(self, new_rate):
        tax_rate = new_rate

    @property
    def tgr(self):
        return self._tgr
    @tgr.setter
    def tgr(self, new_tgr):
        self._tgr = new_tgr

    @property
    def info(self):
        return self._info

    @property
    def financials(self):
        return self._financials

    @property
    def balance_sheet(self):
        return self._balance_sheet
    
    @property
    def cash_flow(self):
        return self._cash_flow


    def revenue(self, projected):
        df_revenue = self._financials.loc[['Total Revenue']]
        if projected is True:
            for i in range(self._period):
                # Projecting revenues with corresponding revenue growth rates
                last_rev = df_revenue.iat[0, -1]
                next_rev = last_rev * (1 + self._rev_growth_rate[i])
                df_revenue[i + 1] = [next_rev]
        return df_revenue

    def ebitda(self, projected):
        # EBITDA = EBIT + D&A
        ebit = self._financials.loc[['Ebit']]
        depreciation = self._cash_flow.loc[['Depreciation']]
        df_calc_ebitda = pd.concat([ebit, depreciation])
        df_calc_ebitda.loc['EBITDA'] = df_calc_ebitda.sum()
        df_ebitda = df_calc_ebitda.loc[['EBITDA']]
        if projected is True:
            # Calculating % of revenue and averaging for projection
            df_revenue = self.revenue(projected=False)
            percents_rev = df_ebitda.loc['EBITDA'].div(df_revenue.loc['Total Revenue'])
            avg_percent_rev = pd.Series.mean(percents_rev)
            df_revenue = self.revenue(projected=True)
            for i in range(self._period):
                projected_ebitda = df_revenue.loc['Total Revenue'].at[i + 1] * avg_percent_rev
                df_ebitda[i + 1] = [projected_ebitda]
        return df_ebitda

    def capex(self, projected):
        df_capex = -self.cash_flow.loc[['Capital Expenditures']]
        if projected is True:
            # Calculating % of revenue and averaging for projection
            df_revenue = self.revenue(projected=False)
            percents_rev = df_capex.loc['Capital Expenditures'].div(df_revenue.loc['Total Revenue'])
            avg_percent_rev = pd.Series.mean(percents_rev)
            df_revenue = self.revenue(projected=True)
            for i in range(self._period):
                projected_capex = df_revenue.loc['Total Revenue'].at[i + 1] * avg_percent_rev
                df_capex[i + 1] = [projected_capex]
        return df_capex
    
    # TODO: actually calculate the change bruh
    def change_in_nwc(self, projected):
        # Change in NWC = Total Current Assets - Total Current Liabilities
        assets = self._balance_sheet.loc[['Total Current Assets']]
        liabilities = -self._balance_sheet.loc[['Total Current Liabilities']]
        df_calc_nwc = pd.concat([assets, liabilities])
        df_calc_nwc.loc['Change in NWC'] = df_calc_nwc.sum()
        df_nwc = df_calc_nwc.loc[['Change in NWC']]
        if projected is True:
            # Calculating % of revenue and averaging for projection
            df_revenue = self.revenue(projected=False)
            percents_rev = df_nwc.loc['Change in NWC'].div(df_revenue.loc['Total Revenue'])
            avg_percent_rev = pd.Series.mean(percents_rev)
            df_revenue = self.revenue(projected=True)
            for i in range(self._period):
                projected_nwc = df_revenue.loc['Total Revenue'].at[i + 1] * avg_percent_rev
                df_nwc[i + 1] = [projected_nwc]
        return df_nwc

    # TODO: fix negative tax messing up projected taxes
    def taxes(self, projected):
        df_taxes = self._financials.loc[['Income Tax Expense']]
        if projected is True:
            # Calculating % of EBITDA and averaging for projection
            df_ebitda = self.ebitda(projected=False)
            percents_ebitda = df_taxes.loc['Income Tax Expense'].div(df_ebitda.loc['EBITDA'])
            avg_percent_ebitda = pd.Series.mean(percents_ebitda)
            df_ebitda = self.ebitda(projected=True)
            for i in range(self._period):
                projected_taxes = df_ebitda.loc['EBITDA'].at[i + 1] * avg_percent_ebitda
                df_taxes[i + 1] = [projected_taxes]
        return df_taxes
    
    def unlevered_fcf(self):
        # Unlevered Free Cash Flow = EBITDA - CapEx - Change in NWC - Taxes
        df_ebitda = self.ebitda(projected=True)
        df_capex = self.capex(projected=True)
        df_nwc = self.change_in_nwc(projected=True)
        df_taxes = self.taxes(projected=True)
        df_calc_ufcf = pd.concat([df_ebitda, -df_capex, -df_nwc, -df_taxes])
        df_calc_ufcf.loc['Unlevered FCF'] = df_calc_ufcf.sum()
        df_ufcf = df_calc_ufcf.loc[['Unlevered FCF']]
        return df_ufcf

