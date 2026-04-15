-- Migration 004: Add object_position to product_images
-- Controls CSS object-position for each image in the collection grid
-- Run in Supabase SQL Editor

ALTER TABLE product_images
  ADD COLUMN IF NOT EXISTS object_position TEXT DEFAULT 'center';
