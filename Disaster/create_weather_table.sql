-- Create Weather Data Table for Disaster Management System
-- Copy and paste this entire script into your Supabase SQL Editor

-- Create the weather_data table
CREATE TABLE IF NOT EXISTS public.weather_data (
  id BIGSERIAL PRIMARY KEY,
  location TEXT NOT NULL,
  temperature NUMERIC(5,2),
  humidity INTEGER,
  wind_speed NUMERIC(5,2),
  weather_condition TEXT,
  is_extreme BOOLEAN DEFAULT FALSE,
  weather_alert TEXT,
  fetched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add weather columns to announcements table
ALTER TABLE public.announcements 
ADD COLUMN IF NOT EXISTS weather_data_id BIGINT REFERENCES public.weather_data(id),
ADD COLUMN IF NOT EXISTS is_weather_alert BOOLEAN DEFAULT FALSE;

-- Grant permissions for Supabase
GRANT ALL ON public.weather_data TO authenticated;
GRANT ALL ON public.weather_data TO anon;
GRANT USAGE ON SEQUENCE public.weather_data_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE public.weather_data_id_seq TO anon;

-- Insert a test record to verify the table works
INSERT INTO public.weather_data (location, temperature, humidity, wind_speed, weather_condition, is_extreme, weather_alert) 
VALUES ('Test Location', 25.5, 60, 5.2, 'Clear', FALSE, NULL)
ON CONFLICT DO NOTHING;

-- Verify the table was created
SELECT 'Weather data table created successfully!' as status;