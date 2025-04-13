import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from arch import arch_model
import plotly.express as px
from datetime import datetime, timedelta
from statsmodels.stats.diagnostic import het_arch
from statsmodels.stats.diagnostic import acorr_ljungbox
import statsmodels.api as sm

# The main title for Streamlit Site
st.title("📈 Stock Volatility Forecasting Analysis Tool using GARCH")

# Data fetching function from Yahoo Finance library (YFinance)
@st.cache_data
def fetch_data(ticker, start_date):

    end_date = datetime.now()

    try:
        data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False, progress=False)

        if data.empty:
            raise ValueError("No data returned for ticker {ticker}. Is it a valid symbol?")

        if 'Adj Close' not in data.columns:
            st.error("No data returned.")
            return None

        return data['Adj Close']

    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {e}")
        return None


# Setting the default values for initial sidebar plot - This is essentially stored in memory
default_ticker = "MSFT"
default_start_date = datetime(2022, 1, 1)

# Sidebar input parameters for user [user interface]
st.sidebar.header("⚙️ Input Parameters")

ticker = st.sidebar.text_input("Stock Ticker (e.g., AAPL)", default_ticker).upper()

startDate = st.sidebar.date_input("Start Date", default_start_date)

forecastDays = st.sidebar.slider("Forecast Days", 1, 100, 10)

price_data = fetch_data(ticker, startDate)


# Sidebar: Historical price plot WHY IS THIS NOT UPDATING - Side thought here, the main issue at hand seems to be an
# inefficient flow of data. The sidebar plot is not picking up the updated values and the fix here would be solving that.
if price_data is not None:
    price_values = price_data.to_numpy().flatten() if price_data.ndim > 1 else price_data.values

    price_df = pd.DataFrame({'Date': price_data.index, 'Price': price_values})

    fig_price = px.line(
        price_df,
        x='Date',
        y='Price',
        title=f"📈 Historical Price for {ticker}",
        color_discrete_sequence=['#1f77b4'],
        labels={'Price': 'Price (USD)', 'Date': 'Date'},
        template='plotly'
    )

    fig_price.update_traces(line=dict(width=2))

    fig_price.update_layout(
        showlegend=False,
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_rangeslider_visible=True,
        yaxis=dict(fixedrange=False)
    )

    st.sidebar.plotly_chart(fig_price, use_container_width=True)


# Sidebar: Instructions
st.sidebar.subheader("Instructions")

st.sidebar.write("""
- Enter a stock ticker (e.g., 'AAPL' for Apple).
- Select a start date for historical data.
- Adjust the forecast horizon to predict future volatility.
- View the given plot and metrics on the right.
""")

st.sidebar.subheader("Acknowledgements")

st.sidebar.write("""
- Project run by **Ubayd Knight** (Current Final Year Student at the University of Huddersfield)
- This website currently runs on **Streamlit** and utilises **pandas**, **numpy**, **yfinance**, **arch**, **plotly**, and **statsmodels** libraries for functionality..
""")

# Update price_data with user input
price_data = fetch_data(ticker, startDate)


# Main panel: Volatility forecast and diagnostics
if price_data is not None:

    # Calculate returns
    returns = 100 * np.log(price_data / price_data.shift(1)).dropna()
    returns_values = returns.to_numpy().flatten() if returns.ndim > 1 else returns.values

    # Historical volatility
    hist_vol = pd.Series(returns_values).rolling(window=21).std() * np.sqrt(252)
    hist_vol = hist_vol.dropna()

    try:
        # GARCH model
        model = arch_model(returns_values, vol='Garch', p=1, q=1, dist='Normal', rescale=True, mean='zero')
        garch_fit = model.fit(disp='off')

        # Forecast volatility
        forecast = garch_fit.forecast(horizon=forecastDays)
        forecast_variance = forecast.variance.iloc[-1].values
        forecast_vol = np.sqrt(forecast_variance) * np.sqrt(252)

        last_date = returns.index[-1]
        forecast_dates = pd.date_range(start=last_date + timedelta(days=1),
                                       periods=forecastDays, freq='B')

        # Debug prints for forecast line
        print(f"forecast_vol shape: {forecast_vol.shape}, values: {forecast_vol[:5]}")
        print(f"forecast_dates length: {len(forecast_dates)}")
        print(f"hist_vol shape: {hist_vol.shape}, values: {hist_vol[-5:].values}")

        # They have to be one-dimensional arrays for compatibility
        hist_vol_values = hist_vol.to_numpy().flatten() if hist_vol.ndim > 1 else hist_vol.values
        forecast_vol_values = forecast_vol.flatten() if forecast_vol.ndim > 1 else forecast_vol

        # Combine historical and forecast volatility
        hist_df = pd.DataFrame({
            'Date': hist_vol.index,
            'Volatility': hist_vol_values,
            'Type': 'Historical'
        })

        forecast_df = pd.DataFrame({
            'Date': forecast_dates,
            'Volatility': forecast_vol_values,
            'Type': 'Forecast'
        })

        print(f"hist_df shape: {hist_df.shape}, forecast_df shape: {forecast_df.shape}")

        vol_df = pd.concat([hist_df, forecast_df], ignore_index=True) #combine both

        print(f"vol_df shape: {vol_df.shape}, unique Types: {vol_df['Type'].unique()}")

        # Volatility plot
        fig_vol = px.line(
            vol_df,
            x='Date',
            y='Volatility',
            color='Type',
            title=f"Volatility Forecast for {ticker}",
            color_discrete_map={'Historical': '#1f77b4', 'Forecast': '#ff7f0e'}, #why does the forecasted plot not display?
            labels={'Volatility': 'Annualised Volatility (%)', 'Date': 'Date'},
            template='plotly_dark'
        )


        fig_vol.update_traces(
            line=dict(width=2),
            selector=dict(name='Historical')
        )

        fig_vol.update_traces(
            line=dict(width=2, dash='dash'),
            selector=dict(name='Forecast')
        )

        fig_vol.update_layout(
            legend=dict(x=0.01, y=0.99),
            showlegend=True,
            xaxis_rangeslider_visible=True,
            yaxis=dict(range=[0, max(vol_df['Volatility'].max() * 1.1, 10)])
        )


        fig_vol.update_xaxes(
            rangeslider_visible=True,
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            )
        )

        st.plotly_chart(fig_vol, use_container_width=True)


        # Model summary
        st.subheader("Model Summary")
        st.write(garch_fit.summary())

        # Beginning of Diagnostic tests; Perhaps look back into the Econometrics tests to properly integrate testing as
        # well as improving on the statement of what those tests mean for the stock selected. Maybe select more tests
        # Maybe refine the GARCH model

        st.subheader("GARCH Model Diagnostic Tests")
        resid = garch_fit.resid
        std_resid = resid / garch_fit.conditional_volatility

        # ARCH-LM test
        arch_lm_test = het_arch(std_resid, nlags=10)
        arch_lm_data = {
            "Metric": ["Test Statistic", "P-value", "Interpretation"],
            "Value": [
                f"{arch_lm_test[0]:.4f}",
                f"{arch_lm_test[1]:.4f}",
                "Low p-value (< 0.05) suggests remaining ARCH effects."
            ]
        }

        st.write("**ARCH-LM Test for Residual ARCH Effects**")
        st.write(
            "The ARCH-LM Test examines whether the GARCH model has fully captured the volatility clustering in the stock's returns. A high test statistic or a low p-value indicates that there may still be patterns of volatility that the model hasn't accounted for, suggesting a need for model refinement.")
        st.table(pd.DataFrame(arch_lm_data))

        # Sign Bias test
        neg_shock = (std_resid < 0).astype(int)
        pos_shock = (std_resid > 0).astype(int)

        sign_bias_data = pd.DataFrame({
            'std_resid_sq': std_resid[1:] ** 2,
            'Negative Shock': neg_shock[:-1],
            'Positive Shock': pos_shock[:-1],
            'Constant': 1
        }).dropna()

        X = sign_bias_data[['Constant', 'Negative Shock', 'Positive Shock']]
        y = sign_bias_data['std_resid_sq']

        sign_bias_model = sm.OLS(y, X).fit()

        sign_bias_results = pd.DataFrame({
            "Coefficient": sign_bias_model.params,
            "Std Error": sign_bias_model.bse,
            "P-value": sign_bias_model.pvalues
        }).round(4)

        st.subheader("**Sign Bias Test**")

        st.write("**Sign Bias Test for Asymmetric Volatility**")
        st.write(
            "The Sign Bias Test checks whether positive and negative stock return shocks have different impacts on future volatility. For example, a sharp price drop might cause more volatility than a similar-sized gain. Significant p-values for the negative or positive shock coefficients suggest the GARCH model may not fully capture these asymmetric effects.")

        st.table(sign_bias_results)

        st.markdown("**Interpretation**: If the p-values for the negative or positive shock coefficients are low (p < 0.05), it suggests that the GARCH model may not fully account for differences in how price drops versus gains affect future volatility, indicating a potential need for a model that handles asymmetry, like an EGARCH.")

        # Ljung-Box test
        lb_test = acorr_ljungbox(std_resid, lags=[10], return_df=True)

        lb_data = {
            "Metric": ["Test Statistic (lag 10)", "P-value (lag 10)", "Interpretation"],
            "Value": [
                f"{lb_test['lb_stat'].iloc[0]:.4f}",
                f"{lb_test['lb_pvalue'].iloc[0]:.4f}",
                "Low p-value (< 0.05) indicates autocorrelation in residuals."
            ]
        }

        st.subheader("**Ljung-Box Test for Autocorrelation**")

        st.write("**Ljung-Box Test for Residual Patterns**")
        st.write(
            "The Ljung-Box Test assesses whether the GARCH model's residuals (errors) show any lingering patterns over time, which could indicate that the model is missing key dynamics in the stock's returns. A low p-value suggests autocorrelation, meaning the model might need additional lags or adjustments to better fit the data.")

        st.table(pd.DataFrame(lb_data))

        # Stability check
        params = garch_fit.params

        stability_data = {"Metric": [], "Value": []}

        if 'alpha[1]' in params and 'beta[1]' in params:
            persistence = params['alpha[1]'] + params['beta[1]']
            stability_data["Metric"].extend(["Persistence (α + β)", "Result"])
            stability_data["Value"].extend([
                f"{persistence:.4f}",
                "Stationary (α + β < 1)" if persistence < 1 else "Non-stationary (α + β ≥ 1)"
            ])

        else:

            stability_data["Metric"].append("Result")
            stability_data["Value"].append("Unable to compute persistence.")

        st.subheader("**GARCH Stability Check**")
        st.write("**GARCH Stability Check for Model Reliability**")
        st.write(
            "The GARCH Stability Check evaluates whether the model's volatility predictions are stable over time by examining the sum of its key parameters (α + β). A value less than 1 indicates a stationary model, meaning volatility shocks fade out, making the model reliable for forecasting. A value at or above 1 suggests instability, where volatility could grow indefinitely.")
        st.table(pd.DataFrame(stability_data))

        # Volatility metrics
        latest_hist_vol = hist_vol[-1] if not hist_vol.empty else np.nan
        first_forecast_vol = forecast_vol[0] if len(forecast_vol) > 0 else np.nan

        st.metric("Latest Historical Volatility", f"{latest_hist_vol:.2f}%")
        st.metric(f"{forecastDays}-Day Forecast Volatility (Day 1)", f"{first_forecast_vol:.2f}%")

    except Exception as e:
        st.error(f"Error fitting GARCH model: {e}")

    else:
        st.warning("Please enter a valid ticker to proceed.")

# Debugging for volatility plot
print(hist_vol.min(), hist_vol.max())
print(forecast_vol.min(), forecast_vol.max())