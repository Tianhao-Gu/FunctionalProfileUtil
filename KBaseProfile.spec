/*
A KBase module: KBaseProfile
*/

module KBaseProfile {

    /* A boolean - 0 for false, 1 for true.
      @range (0, 1)
    */
    typedef int bool;

    /* Ref to a WS object
      @id ws
    */
    typedef string WSRef;

    /*
      A simple 2D matrix of values with labels/ids for rows and
      columns.  The matrix is stored as a list of lists, with the outer list
      containing rows, and the inner lists containing values for each column of
      that row.  Row/Col ids should be unique.

      row_ids - unique ids for rows.
      col_ids - unique ids for columns.
      values - two dimensional array indexed as: values[row][col]

      @metadata ws length(row_ids) as n_rows
      @metadata ws length(col_ids) as n_cols
    */
    typedef structure {
      list<string> row_ids;
      list<string> col_ids;
      list<list<float>> values;
    } FloatMatrix2D;

    /*
      A structure that captures an understanding of the functional capabilities of
      organisms and communities

      sample_set_ref - associated with community_profile
      amplicon_set_ref - associated with organism_profile

      data_epistemology - how was data acquired. one of: measured, asserted, predicted
      epistemology_method - method/program to be used to acquire data. e.g. FAPROTAX, PICRUSt2
      profile_type - type of profile. e.g. amplicon, MG
      profile_category - category of profile. one of community or organism

      @optional original_matrix_ref sample_set_ref amplicon_set_ref
      @optional data_epistemology epistemology_method description profile_type profile_category

      @metadata ws original_matrix_ref as original_matrix_ref
      @metadata ws sample_set_ref as sample_set_ref
      @metadata ws amplicon_set_ref as amplicon_set_ref
      @metadata ws length(data.row_ids) as row_count
      @metadata ws length(data.col_ids) as col_count
      @metadata ws data_epistemology as data_epistemology
      @metadata ws epistemology_method as epistemology_method
      @metadata ws description as description
      @metadata ws profile_type as profile_type
      @metadata ws profile_category as profile_category
    */
    typedef structure {
      WSRef original_matrix_ref;
      WSRef sample_set_ref;
      WSRef amplicon_set_ref;
      FloatMatrix2D data;

      string data_epistemology;
      string epistemology_method;
      string description;
      string profile_type;
      string profile_category;

    } FunctionalProfile;

};
