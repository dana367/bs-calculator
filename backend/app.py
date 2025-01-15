from math import exp, log, sqrt
from typing import Dict, Union

import aiosqlite
from pydantic import BaseModel, Field
from quart import Quart, render_template
from quart_schema import QuartSchema, validate_request
from scipy.stats import norm

app = Quart(__name__)
schema = QuartSchema(app)

DATABASE_URL = "bs.db"


@app.get("/")
async def index():
    return await render_template("index.html")


class BlackScholesInput(BaseModel):
    stock_price: float = Field(..., gt=0, description="Current stock price")
    strike_price: float = Field(..., gt=0, description="Strike price")
    time_to_maturity: float = Field(..., gt=0, description="Time to maturity in years")
    risk_free_rate: float = Field(..., description="Risk-free interest rate")
    dividend_yield: float = Field(..., ge=0, description="Dividend yield")
    volatility: float = Field(..., gt=0, le=1, description="Volatility")


def calculate_black_scholes(
    S: float, X: float, T: float, r: float, q: float, v: float
) -> dict:
    """
    Calculate Black-Scholes option prices

    Args:
        S (float): Stock price
        X (float): Strike price
        T (float): Time to maturity
        r (float): Risk-free rate
        q (float): Dividend yield
        v (float): Volatility
    """
    try:
        d1 = (log(S / X) + (r - q + (v**2) / 2) * T) / (v * sqrt(T))
        d2 = d1 - v * sqrt(T)

        call_price = S * exp(-q * T) * norm.cdf(d1) - X * exp(-r * T) * norm.cdf(d2)
        put_price = X * exp(-r * T) * norm.cdf(-d2) - S * exp(-q * T) * norm.cdf(-d1)

        return {
            "call_option_price": round(call_price, 4),
            "put_option_price": round(put_price, 4),
        }
    except Exception as e:
        raise Exception(f"Black-Scholes calculation failed: {str(e)}")


@app.post("/calculate")
@validate_request(BlackScholesInput)
async def calculate(data: BlackScholesInput):
    """Calculate option prices using Black-Scholes formula"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        try:
            results = calculate_black_scholes(
                S=data.stock_price,
                X=data.strike_price,
                T=data.time_to_maturity,
                r=data.risk_free_rate,
                q=data.dividend_yield,
                v=data.volatility,
            )

            # Insert calculation and get ID
            cursor = await db.execute(
                """
                INSERT INTO calculations 
                (stock_price, strike_price, time_to_maturity, risk_free_rate, 
                dividend_yield, volatility, call_option_price, put_option_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.stock_price,
                    data.strike_price,
                    data.time_to_maturity,
                    data.risk_free_rate,
                    data.dividend_yield,
                    data.volatility,
                    results["call_option_price"],
                    results["put_option_price"],
                ),
            )
            await db.commit()
            calculation_id = cursor.lastrowid

            # Get the timestamp
            cursor = await db.execute(
                "SELECT timestamp FROM calculations WHERE id = ?", (calculation_id,)
            )
            row = await cursor.fetchone()
            timestamp = row[0] if row else None

            # Prepare calculation data
            calculation = {
                "id": calculation_id,
                "stock_price": data.stock_price,
                "strike_price": data.strike_price,
                "time_to_maturity": data.time_to_maturity,
                "risk_free_rate": data.risk_free_rate,
                "dividend_yield": data.dividend_yield,
                "volatility": data.volatility,
                "call_option_price": results["call_option_price"],
                "put_option_price": results["put_option_price"],
                "timestamp": timestamp,
            }

            # Set content type to HTML
            headers = {"Content-Type": "text/html"}
            return (
                await render_template("results.html", calculation=calculation),
                200,
                headers,
            )

        except Exception as e:
            return {"error": f"Calculation failed: {str(e)}"}, 500


@app.get("/calculations")
async def get_calculations():
    """Get all calculations with pagination"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        try:
            async with db.execute(
                """
                SELECT id, stock_price, strike_price, time_to_maturity, 
                       risk_free_rate, dividend_yield, volatility, 
                       call_option_price, put_option_price, timestamp
                FROM calculations 
                ORDER BY timestamp DESC 
                LIMIT 100
                """
            ) as cursor:
                rows = await cursor.fetchall()

            return {
                "calculations": [
                    {
                        "id": row[0],
                        "stock_price": row[1],
                        "strike_price": row[2],
                        "time_to_maturity": row[3],
                        "risk_free_rate": row[4],
                        "dividend_yield": row[5],
                        "volatility": row[6],
                        "call_option_price": row[7],
                        "put_option_price": row[8],
                        "timestamp": row[9],
                    }
                    for row in rows
                ]
            }
        except Exception as e:
            raise Exception(f"Failed to fetch calculations: {str(e)}")


@app.get("/calculations/<int:calc_id>")
async def get_calculation(calc_id: int):
    """Get a specific calculation by ID"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        try:
            async with db.execute(
                """
                SELECT id, stock_price, strike_price, time_to_maturity, 
                       risk_free_rate, dividend_yield, volatility, 
                       call_option_price, put_option_price, timestamp
                FROM calculations 
                WHERE id = ?
                """,
                (calc_id,),
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                return {"error": "Calculation not found"}, 404

            return {
                "id": row[0],
                "stock_price": row[1],
                "strike_price": row[2],
                "time_to_maturity": row[3],
                "risk_free_rate": row[4],
                "dividend_yield": row[5],
                "volatility": row[6],
                "call_option_price": row[7],
                "put_option_price": row[8],
                "timestamp": row[9],
            }
        except Exception as e:
            raise Exception(f"Failed to fetch calculation: {str(e)}")


@app.errorhandler(Exception)
async def handle_error(error):
    """Global error handler"""
    return {"error": str(error), "status": "error"}, 500


if __name__ == "__main__":
    app.run(debug=True)
