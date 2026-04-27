from math import sqrt
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from app.services.data_service import data_service


class ForecastService:
    """Сервис для прогнозирования численности населения"""
    
    def __init__(self):
        self.data_service = data_service

    def _field(self, item: Any, name: str):
        if item is None:
            return None
        if isinstance(item, dict):
            return item.get(name)
        return getattr(item, name, None)

    def _mae(self, actual: np.ndarray, predicted: np.ndarray) -> float:
        return float(np.mean(np.abs(actual - predicted)))

    def _rmse(self, actual: np.ndarray, predicted: np.ndarray) -> float:
        return float(sqrt(np.mean((actual - predicted) ** 2)))

    def _mape(self, actual: np.ndarray, predicted: np.ndarray) -> float:
        nonzero_mask = actual != 0
        if not np.any(nonzero_mask):
            return 0.0
        return float(np.mean(np.abs((actual[nonzero_mask] - predicted[nonzero_mask]) / actual[nonzero_mask])) * 100)
    
    def get_municipality_history(self, code: str) -> List[Dict]:
        """
        Получает исторические данные по муниципалитету за все доступные годы
        """
        years = sorted(self.data_service.get_available_years())
        history = []
        
        for year in years:
            data = self.data_service.get_municipality(code, year)
            if data:
                history.append(
                    {
                        "year": year,
                        "value": self._field(data, "total_population"),
                        "urban": self._field(data, "urban_population"),
                        "rural": self._field(data, "rural_population"),
                    }
                )
        
        return history
    
    def get_region_history(self, region_name: str) -> List[Dict]:
        """
        Получает исторические данные по региону (сумма всех муниципалитетов региона)
        """
        years = sorted(self.data_service.get_available_years())
        history = []
        
        for year in years:
            region_data = self.data_service.get_region_by_name(region_name, year)
            if region_data is None:
                municipalities = self.data_service.get_regions(year)
                for municipality in municipalities:
                    if region_name.lower() in self._field(municipality, "name").lower():
                        region_data = municipality
                        break

            if region_data:
                history.append(
                    {
                        "year": year,
                        "value": self._field(region_data, "total_population"),
                        "urban": self._field(region_data, "urban_population"),
                        "rural": self._field(region_data, "rural_population"),
                    }
                )
        
        return history
    
    def get_russia_history(self) -> List[Dict]:
        """
        Получает исторические данные по России в целом
        """
        years = sorted(self.data_service.get_available_years())
        history = []
        
        for year in years:
            stats = self.data_service.get_year_statistics(year)
            if stats:
                history.append(
                    {
                        "year": year,
                        "value": self._field(stats, "total_population"),
                        "urban": self._field(stats, "urban_population"),
                        "rural": self._field(stats, "rural_population"),
                    }
                )
        
        return history
    
    def get_all_municipalities_with_history(self) -> List[Dict]:
        """
        Получает историю для всех муниципалитетов
        """
        latest_year = max(self.data_service.get_available_years())
        municipalities = self.data_service.get_regions(latest_year)
        
        result = []
        for municipality in municipalities[:100]:
            history = self.get_municipality_history(self._field(municipality, "code"))
            if len(history) >= 3:
                result.append(
                    {
                        "code": self._field(municipality, "code"),
                        "name": self._field(municipality, "name"),
                        "history": history,
                    }
                )
        
        return result
    
    def forecast_linear(self, years: List[int], values: List[float], years_ahead: int) -> Dict:
        """
        Линейная регрессия для прогнозирования
        """
        years_array = np.array(years, dtype=float)
        values_array = np.array(values, dtype=float)

        if len(years_array) < 2:
            slope = 0.0
            intercept = float(values_array[-1]) if len(values_array) else 0.0
            predictions = np.full(len(values_array), intercept)
        else:
            slope, intercept = np.polyfit(years_array, values_array, 1)
            predictions = slope * years_array + intercept

        last_year = years[-1]
        forecast_years = list(range(last_year + 1, last_year + years_ahead + 1))
        forecast_values = slope * np.array(forecast_years, dtype=float) + intercept

        residuals = values_array - predictions
        std_residuals = np.std(residuals)
        confidence_interval = 1.96 * std_residuals

        forecast = [
            {
                "year": int(forecast_years[i]),
                "value": max(0, int(forecast_values[i])),
                "lower_bound": max(0, int(forecast_values[i] - confidence_interval)),
                "upper_bound": int(forecast_values[i] + confidence_interval)
            }
            for i in range(len(forecast_years))
        ]

        ss_res = float(np.sum((values_array - predictions) ** 2))
        ss_tot = float(np.sum((values_array - np.mean(values_array)) ** 2))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 1.0

        return {
            "forecast": forecast,
            "metrics": {
                "mae": round(self._mae(values_array, predictions), 2),
                "rmse": round(self._rmse(values_array, predictions), 2),
                "mape": round(self._mape(values_array, predictions), 2),
                "r_squared": round(r_squared, 4),
            },
            "model_params": {
                "slope": float(slope),
                "intercept": float(intercept),
            },
        }
    
    def forecast_exponential(self, years: List[int], values: List[float], years_ahead: int) -> Dict:
        """
        Экспоненциальное сглаживание для прогнозирования
        """
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing

            series = pd.Series(values, index=years)
            model = ExponentialSmoothing(
                series, 
                trend='additive', 
                seasonal=None,
                initialization_method='estimated',
            )
            fitted_model = model.fit()
            forecast = fitted_model.forecast(years_ahead)

            last_year = years[-1]
            forecast_years = list(range(last_year + 1, last_year + years_ahead + 1))

            residuals = series - fitted_model.fittedvalues
            std_residuals = np.std(residuals.dropna())
            confidence_interval = 1.96 * std_residuals

            forecast_result = [
                {
                    "year": forecast_years[i],
                    "value": max(0, int(forecast.iloc[i])),
                    "lower_bound": max(0, int(forecast.iloc[i] - confidence_interval)),
                    "upper_bound": int(forecast.iloc[i] + confidence_interval),
                }
                for i in range(len(forecast_years))
            ]

            predictions = fitted_model.fittedvalues
            align_idx = predictions.index.intersection(series.index)
            actual = series[align_idx].to_numpy(dtype=float)
            predicted = predictions[align_idx].to_numpy(dtype=float)

            return {
                "forecast": forecast_result,
                "metrics": {
                    "mae": round(self._mae(actual, predicted), 2),
                    "rmse": round(self._rmse(actual, predicted), 2),
                    "mape": round(self._mape(actual, predicted), 2),
                },
            }
        except Exception as e:
            logger.error(f"Exponential smoothing failed: {e}")
            return self.forecast_linear(years, values, years_ahead)
    
    def forecast_holt(self, years: List[int], values: List[float], years_ahead: int) -> Dict:
        """
        Метод Хольта (линейное экспоненциальное сглаживание с трендом)
        """
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing

            series = pd.Series(values, index=years)
            model = ExponentialSmoothing(
                series,
                trend='additive',
                seasonal=None,
                initialization_method='estimated',
            )
            fitted_model = model.fit()
            forecast = fitted_model.forecast(years_ahead)

            last_year = years[-1]
            forecast_years = list(range(last_year + 1, last_year + years_ahead + 1))

            residuals = series - fitted_model.fittedvalues
            std_residuals = np.std(residuals.dropna())
            confidence_interval = 1.96 * std_residuals

            forecast_result = [
                {
                    "year": forecast_years[i],
                    "value": max(0, int(forecast.iloc[i])),
                    "lower_bound": max(0, int(forecast.iloc[i] - confidence_interval)),
                    "upper_bound": int(forecast.iloc[i] + confidence_interval),
                }
                for i in range(len(forecast_years))
            ]

            predictions = fitted_model.fittedvalues
            align_idx = predictions.index.intersection(series.index)
            actual = series[align_idx].to_numpy(dtype=float)
            predicted = predictions[align_idx].to_numpy(dtype=float)

            return {
                "forecast": forecast_result,
                "metrics": {
                    "mae": round(self._mae(actual, predicted), 2),
                    "rmse": round(self._rmse(actual, predicted), 2),
                    "mape": round(self._mape(actual, predicted), 2),
                },
            }
        except Exception as e:
            logger.error(f"Holt method failed: {e}")
            return self.forecast_linear(years, values, years_ahead)
    
    def forecast_auto(self, years: List[int], values: List[float], years_ahead: int) -> Dict:
        """
        Автоматический выбор лучшей модели
        """
        models = {
            'linear': self.forecast_linear,
            'exponential': self.forecast_exponential,
            'holt': self.forecast_holt
        }
        
        best_model = None
        best_mape = float('inf')
        best_result = None
        
        for name, model_func in models.items():
            try:
                result = model_func(years, values, years_ahead)
                if result['metrics']['mape'] < best_mape:
                    best_mape = result['metrics']['mape']
                    best_model = name
                    best_result = result
            except Exception as e:
                logger.warning(f"Model {name} failed: {e}")
                continue
        
        if best_result is None:
            best_result = self.forecast_linear(years, values, years_ahead)
            best_model = "linear (fallback)"
        
        best_result['model_used'] = best_model
        return best_result
    
    def forecast(
        self, 
        historical_data: List[Dict], 
        years_ahead: int,
        model_type: str = "auto"
    ) -> Dict:
        """
        Основной метод прогнозирования
        """
        # Извлекаем годы и значения
        years = [item['year'] for item in historical_data]
        values = [item['value'] for item in historical_data]
        
        # Выбираем модель
        if model_type == "linear":
            result = self.forecast_linear(years, values, years_ahead)
            result['model_used'] = "linear_regression"
        elif model_type == "exponential":
            result = self.forecast_exponential(years, values, years_ahead)
            result['model_used'] = "exponential_smoothing"
        elif model_type == "holt":
            result = self.forecast_holt(years, values, years_ahead)
            result['model_used'] = "holt_linear_trend"
        else:  # auto
            result = self.forecast_auto(years, values, years_ahead)
        
        # Добавляем дополнительную информацию
        result['historical_summary'] = {
            "start_year": years[0],
            "end_year": years[-1],
            "start_value": values[0],
            "end_value": values[-1],
            "total_change": values[-1] - values[0],
            "total_change_percent": ((values[-1] - values[0]) / values[0]) * 100 if values[0] > 0 else 0
        }
        
        return result


forecast_service = ForecastService()
