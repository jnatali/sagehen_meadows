%%%%% DataOrganize_v3 %%%%%

% function [Data_int4, Data_final, Names] = DataOrganize_v3()

SaveOn = 0; %DO NOT SAVE

warning('OFF')
% function [WellData3, Names] = DataOrganize_v3()
Data_raw = readtable('Sagehen_groundwater_wells_MASTER.xlsx', 'Sheet', 'Water Level Reading');
%Convert datetime
Data_raw.Time = datetime(datestr(datenum(Data_raw.Time),'mm/dd/yyyy HH:MM'));
%get names of wellsWE
Names = unique(Data_raw.WellName, 'stable'); 


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% Data intermediate (verified to work)
% Split master table into groups of cell arrays organized by wells, concatenated into table
% for easier visualization

%initialize output table properties
Time = {};
TopToWater_cm_ = {};
WellTopToGround_cm_ = {};
WaterHeightRelativeToGround_cm_ = {};
Logger_ = {};
Water_ = {}; 
MeterVersion = {}; 
FullWellLength_cm_ = {};

%iterate over each well
for i = 1:length(Names)
   index = find(strcmp(Data_raw.WellName, Names{i}));
    Time = [Time; {Data_raw.Time(index)}];
    TopToWater_cm_ = [TopToWater_cm_;{Data_raw.TopToWater_cm_(index)}];
    WellTopToGround_cm_ = [WellTopToGround_cm_;{Data_raw.WellTopToGround_cm_(index)}];
    WaterHeightRelativeToGround_cm_ = [WaterHeightRelativeToGround_cm_;{Data_raw.WaterHeightRelativeToGround_cm_(index)}];
    Logger_ = [Logger_;{Data_raw.Logger_(index)}];
    Water_ = [Water_;{Data_raw.Water_(index)}]; 
    MeterVersion = [MeterVersion; {Data_raw.MeterVersion(index)}];
    FullWellLength_cm_ = [FullWellLength_cm_; Data_raw.FullWellLength_cm_(index)];
end

%create output table
Data_int = table(Names,Time,TopToWater_cm_,WellTopToGround_cm_,...
    WaterHeightRelativeToGround_cm_,Logger_,Water_,MeterVersion, FullWellLength_cm_);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% Edit Well Top To Ground  ** IS WORKING **  **Verified again on 4/3
%If within an indivual dated entry, there is no Top to Gnd measurement, enter the
% mean value of all top to gnd measurements for that well. 
%if there isn't an entry, add the mean

Data_int2 = Data_int;
Flag = {};
WellTop_std = [];
for i = 1:length(Names)
% edit the WellTop to Ground entries, put in the mean if there's a NAN
% values
    s1 = Data_int2.WellTopToGround_cm_{i};
  if all(isnan(s1))
      Flag = [Flag; Names{i}];      %Passes wells that have NO Top 2 Gnd entries
      WellTop_std= [WellTop_std; 0];
  else
    Locs1 = isnan(s1); %indexes of the nan values
    Locs2 = ~isnan(s1); %indexes of the ~isnan values
    avgVal = mean(s1(Locs2)); %mean
    WellTop_std= [WellTop_std; std(s1(Locs2))];
    s1(Locs1) = avgVal;
    Data_int2.WellTopToGround_cm_{i} = s1;
  end
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% Find full length  **Works** *Verified 4/3
 
Data_int3 = Data_int2;
Flag2 = {};
FullLength_std = [];
for i = 1:length(Names)
% edit the Well Full Length entries, put in the mean if there's a NAN
% value
    s1 = Data_int3.FullWellLength_cm_{i};
  if all(isnan(s1))
      Flag2 = [Flag2; Names{i}];     %Passes wells with no full length measurements
      FullLength_std = [FullLength_std; 0];
  else
    Locs1 = isnan(s1); %indexes of the nan values
    Locs2 = ~isnan(s1); %indexes of the ~isnan values
    avgVal = mean(s1(Locs2)); %mean
    FullLength_std = [FullLength_std; std(s1(Locs2))];
    s1(Locs1) = avgVal;
    Data_int3.FullWellLength_cm_{i} = s1;
  end 
end

%% concatenate totally
bleh = table(WellTop_std, FullLength_std);
Data_int4 = [Data_int3, bleh];

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% Find Water Height Relative to Ground
% run meter offset function
% if meter 
% Top2gnd - Top2Water -/+ Meter Offset

%if water{i} = 0
%(now)   pass 
%(later) enter full well length (or something useful for shannon)
%if WaterHeightrel2gnd ~= isnan
%   pass
%else
%   data.WaterHeightrel2gnd{i} = top2gnd - top2h20 +/- Offset
Offset = MeterOffsetOrganize();
Offset = removevars(Offset, {'Offset', 'Notes'});

for i = 1:length(Names) %loop over each well
    for j = 1:length(Data_int4.Time{i}) % loop over each entry for a well
        if Data_int4.Water_{i}(j) == 0   %if no water
%             %edit in the full well length
%             if 
        elseif isnan(Data_int4.Water_{i}(j)) %if there is no entry for Water?
            %pass: don't know what to do with it
            %mostly just documenting presence of logger
        else %water == 1
            % do the equation
            if ~isnan(Data_int4.WaterHeightRelativeToGround_cm_{i}(j))
                %WATER IS ABOVE GROUND AND ALREADY ENTRIED
            else
              m_offset = meteroffset(Offset, Data_int4.MeterVersion{i}{j});
              top2gnd = Data_int4.WellTopToGround_cm_{i}(j);
              top2water = Data_int4.TopToWater_cm_{i}(j);
              Data_int4.WaterHeightRelativeToGround_cm_{i}(j) = top2gnd - top2water - m_offset; 
            end
        end
    end
end
        
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    
%% concatenate into a final master table

%Deal with names
Names_final = {};
for i = 1:length(Names)
    for l = 1:length(Data_int4.Time{i});
    Names_final = [Names_final; Names{i}];
    end
end

Time = vertcat(Data_int4.Time{:});
TopToWater_cm_ = vertcat(Data_int4.TopToWater_cm_{:});
WellTopToGround_cm_ = vertcat(Data_int4.WellTopToGround_cm_{:});
WaterHeightRelativeToGround_cm_ = vertcat(Data_int4.WaterHeightRelativeToGround_cm_{:});
Logger_ = vertcat(Data_int4.Logger_{:});
Water_ = vertcat(Data_int4.Water_{:});
MeterVersion = vertcat(Data_int4.MeterVersion{:});
FullWellLength_cm_ = vertcat(Data_int4.FullWellLength_cm_{:});

Data_final = table(Names_final, Time, TopToWater_cm_, WellTopToGround_cm_,...
    WaterHeightRelativeToGround_cm_, Logger_, Water_, MeterVersion, FullWellLength_cm_);

varName = {'Well Name', 'Time', 'Top To Water(cm)',...
    'Well Top To Ground(cm)', 'Water Height Relative To Ground(cm)',...
    'Logger?', 'Water?', 'Meter Version', 'FullWellLength(cm)'};
Data_final.Properties.VariableNames = varName;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% output to csv

if SaveOn == 1
writetable(Data_final,'GroundwaterMASTER.csv', 'Delimiter', ',')
writetable(Data_final,'GroundwaterMASTER.xlsx')
end
% Output a table for each well (as csv?)

% end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%Subfunction that finds meter offset to use
function m_offset = meteroffset(Offset, meterv);
%'nm','nw', ''
idx = strcmp(Offset.Name, meterv);
if any(idx)
    m_offset = Offset.Avg(idx);
else
    if strcmp(meterv, 'nm')
        m_offset = 0;
    end
end
end
