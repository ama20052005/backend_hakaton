import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.metrics import mean_absolute_error, mean_squared_error
from math import sqrt
from loguru import logger

from app.services.data_service import data_service


class ForecastService:
    """Сервис для прогнозирования численности населения"""
    
    def __init__(self):
        self.data_service = data_service
    
    def get_municipality_history(self, code: str) -> List[Dict]:
        """
        Получает исторические данные по муниципалитету за все доступные годы
        """
        years = sorted(self.data_service.get_available_years())
        history = []
        
        for year in years:
            data = self.data_service.get_municipality(code, year)
            if data:
                history.append({
                    "year": year,
                    "value": data['total_population'],
                    "urban": data['urban_population'],
                    "rural": data['rural_population']
                })
        
        return history
    
    def get_region_history(self, region_name: str) -> List[Dict]:
        """
        Получает исторические данные по региону (сумма всех муниципалитетов региона)
        """
        years = sorted(self.data_service.get_available_years())
        history = []
        
        for year in years:
            # Ищем все муниципалитеты, содержащие название региона
            # Это упрощенный подход - в реальности нужно использовать code региона
            municipalities = self.data_service.get_regions(year)
            region_data = None
            
            for mun in municipalities:
                if region_name.lower() in mun['name'].lower():
                    region_data = mun
                    break
            
            if region_data:
                history.append({
                    "year": year,
                    "value": region_data['total_population'],
                    "urban": region_data['urban_population'],
                    "rural": region_data['rural_population']
                })
        
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
                history.append({
                    "year": year,
                    "value": stats['total_population'],
                    "urban": stats['urban_population'],
                    "rural": stats['rural_population']
                })
        
        return history
    
    def get_all_municipalities_with_history(self) -> List[Dict]:
        """
        Получает историю для всех муниципалитетов
        """
        latest_year = max(self.data_service.get_available_years())
        municipalities = self.data_service.get_regions(latest_year)
        
        result = []
        for mun in municipalities[:100]:  # Ограничиваем для производительности
            history = self.get_municipality_history(mun['code'])
            if len(history) >= 3:
                result.append({
                    "code": mun['code'],
                    "name": mun['name'],
                    "history": history
                })
        
        return result
    
    def forecast_linear(self, years: List[int], values: List[float], years_ahead: int) -> Dict:
        """
        Линейная регрессия для прогнозирования
        """
        X = np.array(years).reshape(-1, 1)
        y = np.array(values)
        
        model = LinearRegression()
        model.fit(X, y)
        
        # Прогноз
        last_year = years[-1]
        forecast_years = list(range(last_year + 1, last_year + years_ahead + 1))
        forecast_values = model.predict(np.array(forecast_years).reshape(-1, 1))
        
        # Расчет доверительных интервалов
        residuals = y - model.predict(X)
        std_residuals = np.std(residuals)
        confidence_interval = 1.96 * std_residuals  # 95% доверительный интервал
        
        forecast = [
            {
                "year": int(forecast_years[i]),
                "value": max(0, int(forecast_values[i])),
                "lower_bound": max(0, int(forecast_values[i] - confidence_interval)),
                "upper_bound": int(forecast_values[i] + confidence_interval)
            }
            for i in range(len(forecast_years))
        ]
        
        # Метрики качества на исторических данных
        predictions = model.predict(X)
        mae = mean_absolute_error(y, predictions)
        rmse = sqrt(mean_squared_error(y, predictions))
        mape = np.mean(np.abs((y - predictions) / y)) * 100
        
        return {
            "forecast": forecast,
            "metrics": {
                "mae": round(mae, 2),
                "rmse": round(rmse, 2),
                "mape": round(mape, 2),
                "r_squared": round(model.score(X, y), 4)
            },
            "model_params": {
                "slope": float(model.coef_[0]),
                "intercept": float(model.intercept_)
            }
        }
    
    def forecast_exponential(self, years: List[int], values: List[float], years_ahead: int) -> Dict:
        """
        Экспоненциальное сглаживание для прогнозирования
        """
        try:
            # Создаем временной ряд
            series = pd.Series(values, index=years)
            
            # Простое экспоненциальное сглаживание
            model = ExponentialSmoothing(
                series, 
                trend='additive', 
                seasonal=None,
                initialization_method='estimated'
            )
            fitted_model = model.fit()
            
            # Прогноз
            forecast = fitted_model.forecast(years_ahead)
            
            last_year = years[-1]
            forecast_years = list(range(last_year + 1, last_year + years_ahead + 1))
            
            # Расчет доверительных интервалов
            residuals = series - fitted_model.fittedvalues
            std_residuals = np.std(residuals.dropna())
            confidence_interval = 1.96 * std_residuals
            
            forecast_result = [
                {
                    "year": forecast_years[i],
                    "value": max(0, int(forecast.iloc[i])),
                    "lower_bound": max(0, int(forecast.iloc[i] - confidence_interval)),
                    "upper_bound": int(forecast.iloc[i] + confidence_interval)
                }
                for i in range(len(forecast_years))
            ]
            
            # Метрики качества
            predictions = fitted_model.fittedvalues
            align_idx = predictions.index.intersection(series.index)
            y_actual = series[align_idx]
            y_pred = predictions[align_idx]
            
            mae = mean_absolute_error(y_actual, y_pred)
            rmse = sqrt(mean_squared_error(y_actual, y_pred))
            mape = np.mean(np.abs((y_actual - y_pred) / y_actual)) * 100
            
            return {
                "forecast": forecast_result,
                "metrics": {
                    "mae": round(mae, 2),
                    "rmse": round(rmse, 2),
                    "mape": round(mape, 2)
                }
            }
        except Exception as e:
            logger.error(f"Exponential smoothing failed: {e}")
            # Fallback to linear
            return self.forecast_linear(years, values, years_ahead)
    
    def forecast_holt(self, years: List[int], values: List[float], years_ahead: int) -> Dict:
        """
        Метод Хольта (линейное экспоненциальное сглаживание с трендом)
        """
        try:
            series = pd.Series(values, index=years)
            
            # Модель Хольта с трендом
            model = ExponentialSmoothing(
                series,
                trend='additive',
                seasonal=None,
                initialization_method='estimated'
            )
            fitted_model = model.fit()
            
            # Прогноз
            forecast = fitted_model.forecast(years_ahead)
            
            last_year = years[-1]
            forecast_years = list(range(last_year + 1, last_year + years_ahead + 1))
            
            # Доверительные интервалы
            residuals = series - fitted_model.fittedvalues
            std_residuals = np.std(residuals.dropna())
            confidence_interval = 1.96 * std_residuals
            
            forecast_result = [
                {
                    "year": forecast_years[i],
                    "value": max(0, int(forecast.iloc[i])),
                    "lower_bound": max(0, int(forecast.iloc[i] - confidence_interval)),
                    "upper_bound": int(forecast.iloc[i] + confidence_interval)
                }
                for i in range(len(forecast_years))
            ]
            
            # Метрики качества
            predictions = fitted_model.fittedvalues
            align_idx = predictions.index.intersection(series.index)
            y_actual = series[align_idx]
            y_pred = predictions[align_idx]
            
            mae = mean_absolute_error(y_actual, y_pred)
            rmse = sqrt(mean_squared_error(y_actual, y_pred))
            mape = np.mean(np.abs((y_actual - y_pred) / y_actual)) * 100
            
            return {
                "forecast": forecast_result,
                "metrics": {
                    "mae": round(mae, 2),
                    "rmse": round(rmse, 2),
                    "mape": round(mape, 2)
                }
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