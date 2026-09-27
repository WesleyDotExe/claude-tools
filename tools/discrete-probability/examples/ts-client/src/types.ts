/** Shape of `compare_two_proportions`'s result, as returned by
 * `tools/discrete-probability/probkit.py` (see that file for the source of
 * truth -- keep this in sync if the tool's return shape changes). */
export interface ProportionGroup {
  successes: number;
  trials: number;
  proportion: number;
  wilson_ci: [number, number];
}

export interface CompareTwoProportionsResult {
  group_a: ProportionGroup;
  group_b: ProportionGroup;
  confidence_level: number;
  difference_a_minus_b: number;
  difference_ci_newcombe: [number, number];
  z_statistic: number;
  p_value: number;
  significant: boolean;
  verdict: string;
  /** Only present when the call passed `verify: true`. */
  simulation?: {
    method: string;
    trials: number;
    empirical_p_value: number;
    empirical_p_value_95_ci: [number, number];
    analytic_p_value: number;
    agrees_on_significance_call: boolean;
    note: string;
  };
}
