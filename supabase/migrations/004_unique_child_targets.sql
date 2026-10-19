-- Abort rather than delete historical cases if duplicates need analyst review.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM cases WHERE parent_case_id IS NOT NULL
        GROUP BY investigation_id, input_type, query HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Duplicate child targets exist; reconcile them before migration 004';
    END IF;
END $$;
CREATE UNIQUE INDEX IF NOT EXISTS uq_child_target
    ON cases (investigation_id, input_type, query)
    WHERE parent_case_id IS NOT NULL;
