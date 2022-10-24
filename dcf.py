import pandas as pd
import yfinance as yf

class DCF:

    def __init__(self, symbol, proj_growth, tgr):
        self._ticker = yf.Ticker(symbol)
        # projected growth rates for operating cash flow
        self._proj_growth = proj_growth
        # forecasting period
        self._period = len(self._proj_growth)
        # terminal growth rate
        self._tgr = tgr

        self._info = self._ticker.info
        # reverse col order (ascending FYE)
        self._financials = self._ticker.financials[self._ticker.financials.columns[::-1]]
        self._balance_sheet = self._ticker.balance_sheet[self._ticker.balance_sheet.columns[::-1]]
        self._cash_flow = self._ticker.cashflow[self._ticker.cashflow.columns[::-1]]
        self._wacc = self.wacc()
        # round all figures to 2 decimal places
        pd.set_option('display.float_format', lambda x: '%.2f' % x)

    def prep(self):
        op_cf = self._cash_flow.loc['Total Cash From Operating Activities']
        capex = self._cash_flow.loc['Capital Expenditures']
        # CapEx as % of operating cash flow
        pcnts_capex_op_cf = capex.multiply(-1).div(op_cf)
        avg_pcnt = pcnts_capex_op_cf.mean()
        df_prep = self._cash_flow.loc[['Total Cash From Operating Activities']]
        df_prep.loc['CapEx'] = capex.multiply(-1)
        for i in range(self._period):
            proj_op_cf = df_prep.iat[0, -1] * (1 + self._proj_growth[i])
            proj_capex = avg_pcnt * proj_op_cf
            df_prep[i + 1] = [proj_op_cf, proj_capex]
        df_prep.loc['Free Cash Flow'] = df_prep.sum()
        return df_prep

    def dcf(self):
        df_dcf = self.prep()
        wacc = self._wacc
        df_dcf.loc['Present Value of FCF'] = 0
        for i in range(self._period):
            curr_fcf = df_dcf.at['Free Cash Flow', i + 1] 
            df_dcf.at['Present Value of FCF', i + 1] = curr_fcf / (1 + wacc)**(i + 1)
        return df_dcf

    def share_price(self):
        df_dcf = self.dcf()
        wacc = self._wacc
        last_fcf = df_dcf.at['Free Cash Flow', self._period]
        tv = (last_fcf * (1 + self._tgr)) / (wacc - self._tgr)
        pv_tv = tv / (1 + wacc)**(self._period)
        enterprise_value = df_dcf.loc['Present Value of FCF'].sum() + pv_tv
        cash = self._balance_sheet.loc['Cash'][-1]
        debt = self._balance_sheet.loc['Long Term Debt'][-1]
        equity_value = enterprise_value + cash - debt
        shares = self._info.get('sharesOutstanding')
        share_price = equity_value / shares
        d = [tv, pv_tv, enterprise_value, cash, debt, equity_value, shares, 
        share_price]
        df_sp = pd.DataFrame(data=d, columns=['All numbers in dollars'])
        df_sp.index = ['Terminal Value', 'Present Value of Terminal Value',
                'Enterprise Value', 'Cash', 'Debt', 'Equity Value', 'Shares',
                'Implied Share Price']
        return df_sp

    def wacc(self):
        # treasury yield for risk free rate
        tnx = yf.Ticker('^TNX')
        rfr = tnx.info.get('previousClose') * 0.01
        # beta
        b = self._info.get('beta')
        # equity risk premium
        erp = 0.056

        # calculate mean tax rate
        taxes = self._financials.loc['Income Tax Expense'].abs()
        ebit = self._financials.loc['Ebit']
        tax_rates = taxes.div(ebit)
        tc = tax_rates.mean()

        # calculate cost of equity
        cost_equity = rfr + b * (erp - rfr)
        # market value of equity (market capitalization)
        e = self._info.get('marketCap')

        # calculate cost of debt
        interests = self._financials.loc['Interest Expense'].multiply(-1)
        debts = self._balance_sheet.loc['Long Term Debt']
        int_rates = interests.div(debts)
        avg_int_rate = int_rates.mean()
        cost_debt = avg_int_rate * (1 - tc)
        # market value of debt (most recent debt figure)
        d = debts[-1]

        # for ratios
        v = e + d

        # equation
        wacc = (e/v * cost_equity) + (d/v * cost_debt * (1 - tc))
        return wacc